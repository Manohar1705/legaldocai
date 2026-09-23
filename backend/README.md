# Backend — Legal Document Assistant

## Setup

```
cp .env.example .env
pip install -r requirements.txt
```

**System dependency (Step 5 — OCR):** the `pytesseract` package is just a
Python wrapper. It calls the `tesseract` binary, which must be installed
separately on the machine running the backend:

- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki

Without this, PDF pages that need OCR (scanned/image-only pages) will fail
extraction with a clear error — native-text PDFs and DOCX files are unaffected
since they don't need OCR.

**First-run model download (Step 6 — embeddings):** the first time the
backend embeds a chunk, `sentence-transformers` downloads the
`all-MiniLM-L6-v2` model (~80MB) from Hugging Face. This needs internet
access **once**; after that it's cached locally
(`~/.cache/huggingface/`) and every run after that is fully offline.
Run the backend at least once with real internet access before a demo
with no wifi.

**Groq API key (Step 8 — chat):** chat requires a `GROQ_API_KEY` in
`.env`. Get a free key at https://console.groq.com/keys and set it —
without it, the chat endpoint returns a clear 502 error rather than
crashing.

## Run

```
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

## Steps completed so far

1. Backend skeleton (FastAPI, config, DB, health check)
2. Auth (register/login/JWT + bcrypt)
3. Design pass (frontend only)
4. Document upload (model, upload/list endpoints, file storage)
5. **Text extraction** — PyMuPDF for native PDF text, pytesseract OCR
   fallback for scanned pages, python-docx for DOCX (including table cells).
   Runs as a background task after upload so the upload response stays fast;
   `status` moves `uploaded → processing → processed/failed`.
6. **Chunking + embeddings** — extracted text is split into overlapping
   ~1000-char chunks (`app/services/chunking.py`), each chunk is embedded
   with sentence-transformers (`all-MiniLM-L6-v2`, 384-dim,
   `app/services/embeddings.py`), and stored in the new `document_chunks`
   table (embedding as a JSON-encoded list in a TEXT column — no vector
   extension needed at this scale; see Step 7 for the similarity search
   that reads these back). Runs as part of the same background task as
   extraction, right after text is pulled from the file.
7. **Similarity search** — `app/services/retrieval.py` embeds the query
   with the same model, loads a document's chunk embeddings into numpy,
   and ranks them by cosine similarity. `GET /documents/{id}/search?q=...`
   is a debug endpoint to sanity-check retrieval quality directly (try it
   in `/docs`) — Step 8's chat endpoint will call the same
   `retrieve_relevant_chunks()` function under the hood.
8. **RAG chat** — `app/services/llm.py` calls Groq's OpenAI-compatible
   chat completions API (`openai/gpt-oss-120b`). `app/services/chat.py`
   retrieves the top matching chunks for the user's question, builds a
   system prompt instructing the model to answer only from those
   excerpts (and say so if the answer isn't there), and includes recent
   conversation history so follow-ups work. `POST /documents/{id}/chat`
   and `GET /documents/{id}/chat` store and return the full conversation
   per document. Frontend: `/documents/:id` is a chat page with message
   bubbles, optimistic sending, and a "still processing" state for
   documents that aren't ready yet.
9. **Summary** — `app/services/summary.py` reuses `call_llm()` from
   Step 8, but runs it over the document's full `extracted_text` instead
   of retrieved chunks, since a summary needs the whole document. The
   result is cached on `Document.summary` / `summarized_at` so repeat
   visits don't re-call the LLM. `POST /documents/{id}/summary` returns
   the cached summary if one exists, generates one otherwise, and
   accepts `?force=true` to regenerate. Frontend adds a Summary tab
   alongside Chat on the document page.

## Not included in this build

Risky-clause detection (flagging unusual terms with severity labels) was
scoped as a later step and intentionally left out of this demo — nothing
else depends on it, so it can be added independently without touching
Steps 1-9.
