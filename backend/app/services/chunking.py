"""
Step 6: chunking.

Splits extracted document text into overlapping chunks small enough to
embed and retrieve individually, while keeping enough overlap that a
clause split across a chunk boundary isn't lost entirely from either side.

Splits on paragraph breaks first (extraction already inserts "\n\n"
between paragraphs/pages/table cells), then packs paragraphs into chunks
up to CHUNK_SIZE_CHARS, falling back to a hard character split only for
a single paragraph that's longer than the chunk size on its own.
"""

CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph

        if len(candidate) <= CHUNK_SIZE_CHARS:
            current = candidate
            continue

        # Adding this paragraph would overflow the chunk — close the
        # current chunk out first.
        if current:
            chunks.append(current)
            current = _overlap_tail(current)

        # Single paragraph longer than a whole chunk (rare, e.g. a
        # dense clause with no internal breaks) — hard-split it.
        if len(paragraph) > CHUNK_SIZE_CHARS:
            for piece in _hard_split(paragraph):
                chunks.append(piece)
            current = ""
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph

    if current:
        chunks.append(current)

    return chunks


def _overlap_tail(chunk: str) -> str:
    """Carry the last bit of a closed chunk forward so context isn't
    lost at the boundary."""
    if len(chunk) <= CHUNK_OVERLAP_CHARS:
        return chunk
    return chunk[-CHUNK_OVERLAP_CHARS:]


def _hard_split(paragraph: str) -> list[str]:
    pieces = []
    start = 0
    while start < len(paragraph):
        end = start + CHUNK_SIZE_CHARS
        pieces.append(paragraph[start:end])
        start = end - CHUNK_OVERLAP_CHARS
    return pieces
