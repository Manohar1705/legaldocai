from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    """
    Step 4: upload only. `stored_filename` is a UUID-based name on disk
    (app/../uploads/), decoupled from the user-supplied `original_filename`
    to avoid collisions and path-traversal issues.
    `status` is a plain string now ("uploaded") — Step 5 will move it through
    "processing" / "processed" / "failed" once extraction is added.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Step 5: text extraction. status now moves
    # uploaded -> processing -> processed / failed.
    extracted_text: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(String(500), nullable=True)

    # Step 9: summary. Generated on demand (not at upload time) and cached
    # here so repeat visits to the summary tab don't re-call the LLM.
    # summarized_at is separate from uploaded_at so the UI can show
    # "summary generated 2 minutes ago" and so a future "regenerate"
    # action has something to update.
    summary: Mapped[str] = mapped_column(String, nullable=True)
    summarized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """
    Step 6: one row per text chunk of a processed document.

    `embedding` stores the vector as a JSON-encoded list of floats in a
    plain TEXT column — there's no vector-search extension in SQLite, so
    Step 7's similarity search loads these back into numpy arrays and
    computes cosine similarity in Python. Swapping this for pgvector later
    means changing the storage/search functions, not this schema's shape.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[str] = mapped_column(String, nullable=False)  # JSON list[float]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


class ChatMessage(Base):
    """
    Step 8: one row per message in a document's chat history.
    `role` is "user" or "assistant" — mirrors the shape the LLM API
    itself expects, so building the message list to send back is a
    direct mapping, not a translation step.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
