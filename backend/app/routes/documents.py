import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user
from app.models import User, Document, DocumentChunk, ChatMessage
from app.schemas import DocumentOut, ChatRequest, ChatMessageOut
from app.services.extraction import extract_text, ExtractionError
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts, serialize_embedding
from app.services.retrieval import retrieve_relevant_chunks
from app.services.chat import answer_question
from app.services.summary import generate_summary
from app.services.llm import LLMError

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024

EXT_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _run_extraction(document_id: int, file_path: str, content_type: str) -> None:
    """
    Runs in a background task, so it gets its own DB session
    (the request's session is already closed by the time this runs).
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return
        document.status = "processing"
        db.commit()

        try:
            text = extract_text(file_path, content_type)
            document.extracted_text = text

            chunks = chunk_text(text)
            if chunks:
                vectors = embed_texts(chunks)
                for index, (chunk_text_value, vector) in enumerate(zip(chunks, vectors)):
                    db.add(
                        DocumentChunk(
                            document_id=document.id,
                            chunk_index=index,
                            text=chunk_text_value,
                            embedding=serialize_embedding(vector),
                        )
                    )

            document.status = "processed"
            document.error_message = None
        except ExtractionError as exc:
            document.status = "failed"
            document.error_message = str(exc)
        except Exception as exc:
            # Embedding step failed even though extraction succeeded —
            # surface it the same way so the UI shows a clear failure
            # instead of silently leaving the document stuck.
            document.status = "failed"
            document.error_message = f"Embedding failed: {exc}"

        db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported.",
        )

    # Read fully to enforce the size cap up front — fine for the MAX_UPLOAD_MB
    # ceiling we set (20MB default); Step 5 can switch to streamed reads if
    # much larger files become a requirement.
    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit.",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    ext = EXT_BY_CONTENT_TYPE.get(file.content_type, "")
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / stored_filename
    dest_path.write_bytes(contents)

    document = Document(
        owner_id=current_user.id,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(
        _run_extraction, document.id, str(dest_path), document.content_type
    )

    return document


def _get_owned_document(document_id: int, current_user: User, db: Session) -> Document:
    document = db.get(Document, document_id)
    # 404, not 403, if it's not theirs — never confirm it exists at all.
    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_document(document_id, current_user, db)


@router.get("/{document_id}/search")
def search_document(
    document_id: int,
    q: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 7 debug endpoint — lets you sanity-check retrieval quality
    directly (e.g. via /docs) before Step 8 wires this into chat.
    Same retrieval function chat will use under the hood.
    """
    document = _get_owned_document(document_id, current_user, db)
    if document.status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is '{document.status}', not ready to search yet.",
        )
    return retrieve_relevant_chunks(db, document_id, q)


@router.post("/{document_id}/summary", response_model=DocumentOut)
def summarize_document(
    document_id: int,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates (and caches) a plain-language summary of the whole document.
    Cached on the document row so revisiting the summary tab doesn't
    re-call the LLM every time; pass ?force=true to regenerate.
    """
    document = _get_owned_document(document_id, current_user, db)
    if document.status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is '{document.status}', not ready to summarize yet.",
        )
    if document.summary and not force:
        return document

    if not document.extracted_text or not document.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has no extracted text to summarize.",
        )

    try:
        summary_text = generate_summary(document.extracted_text)
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    document.summary = summary_text
    document.summarized_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/chat", response_model=ChatMessageOut)
def chat_with_document(
    document_id: int,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document(document_id, current_user, db)
    if document.status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is '{document.status}', not ready to chat with yet.",
        )
    if not body.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    history_rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.created_at)
    ).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_message = ChatMessage(document_id=document_id, role="user", content=body.message)
    db.add(user_message)
    db.commit()

    try:
        answer = answer_question(db, document_id, body.message, history)
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    assistant_message = ChatMessage(document_id=document_id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message


@router.get("/{document_id}/chat", response_model=list[ChatMessageOut])
def get_chat_history(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.created_at)
    )
    return db.execute(stmt).scalars().all()


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
    )
    return db.execute(stmt).scalars().all()
