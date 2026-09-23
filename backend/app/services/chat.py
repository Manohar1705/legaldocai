"""
Step 8: RAG chat orchestration.

Ties retrieval (Step 7) to the LLM (Groq): retrieve the chunks most
relevant to the user's latest message, build a system prompt that
instructs the model to answer only from those chunks, and include
recent conversation history so follow-up questions ("what about the
penalty?") have context.
"""

from sqlalchemy.orm import Session

from app.services.retrieval import retrieve_relevant_chunks
from app.services.llm import call_llm

# How many prior turns (user+assistant pairs) to include for context.
# Kept small since each turn adds tokens to every subsequent request.
MAX_HISTORY_TURNS = 5

SYSTEM_PROMPT_TEMPLATE = """You are a legal document assistant helping a \
non-lawyer understand a contract. Answer the user's question using ONLY \
the document excerpts provided below — do not use outside knowledge, and \
do not guess. If the answer isn't in the excerpts, say so clearly instead \
of making something up. Explain any legal terms in plain, simple language.

Document excerpts:
{context}
"""


def answer_question(db: Session, document_id: int, question: str, history: list[dict]) -> str:
    chunks = retrieve_relevant_chunks(db, document_id, question, top_k=5)

    if not chunks:
        return (
            "I don't have any content indexed for this document yet — "
            "it may still be processing, or extraction may have failed."
        )

    context = "\n\n---\n\n".join(c["text"] for c in chunks)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-(MAX_HISTORY_TURNS * 2):])
    messages.append({"role": "user", "content": question})

    return call_llm(messages)
