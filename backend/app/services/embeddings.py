"""
Step 6: embeddings.

Uses sentence-transformers' all-MiniLM-L6-v2 — small (~80MB), fast on CPU,
384-dimensional vectors, no API key or network call at inference time
(only the first run needs internet, to download model weights once; after
that they're cached locally and everything runs offline).

The model is loaded lazily and cached at module level so it's loaded once
per process, not once per request.
"""

import json

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Returns one embedding vector (list of floats) per input text."""
    if not texts:
        return []
    import numpy as np

    model = _get_model()
    vectors = np.array(list(model.embed(texts)))
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def serialize_embedding(vector: list[float]) -> str:
    return json.dumps(vector)


def deserialize_embedding(raw: str) -> list[float]:
    return json.loads(raw)
