"""
Step 7: similarity search.

No vector database at this scale (see models.py note on DocumentChunk) —
this loads a document's chunk embeddings into numpy and computes cosine
similarity against the query embedding directly in Python. Fine up to a
few hundred chunks per document; if this ever needs to scale to
thousands of documents searched at once, swap this function's internals
for pgvector/ChromaDB without changing its signature.
"""

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import DocumentChunk
from app.services.embeddings import embed_text, deserialize_embedding

DEFAULT_TOP_K = 5


def retrieve_relevant_chunks(
    db: Session, document_id: int, query: str, top_k: int = DEFAULT_TOP_K
) -> list[dict]:
    """
    Returns up to `top_k` chunks for `document_id` most similar to `query`,
    each as {"text": str, "score": float, "chunk_index": int}, sorted by
    score descending. Returns [] if the document has no chunks yet
    (e.g. still processing).
    """
    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).scalars().all()

    if not chunks:
        return []

    query_vector = np.array(embed_text(query))
    chunk_vectors = np.array([deserialize_embedding(c.embedding) for c in chunks])

    scores = _cosine_similarity(query_vector, chunk_vectors)

    ranked_indices = np.argsort(scores)[::-1][:top_k]

    return [
        {
            "text": chunks[i].text,
            "score": float(scores[i]),
            "chunk_index": chunks[i].chunk_index,
        }
        for i in ranked_indices
    ]


def _cosine_similarity(query_vector: np.ndarray, chunk_vectors: np.ndarray) -> np.ndarray:
    """
    Cosine similarity between one query vector and many chunk vectors.
    Works whether or not the vectors are pre-normalized — dividing by
    the actual norms here makes this correct either way (embeddings.py
    normalizes at encode time, but this function doesn't rely on that).
    """
    query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-10)
    chunk_norms = chunk_vectors / (
        np.linalg.norm(chunk_vectors, axis=1, keepdims=True) + 1e-10
    )
    return chunk_norms @ query_norm
