# Backend: Legal Document Assistant

FastAPI service that handles auth, document upload, text extraction,
embeddings, retrieval, and LLM-powered chat and summaries.

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
```

> If `pip` isn't recognized, or packages install into the wrong Python, use `python -m pip install -r requirements.txt` instead.

Then edit `.env`:

- Set `GROQ_API_KEY` (get a free key at https://console.groq.com/keys).
  Without it, chat and summary endpoints return a clear `502` error instead
  of crashing.
- Set `JWT_SECRET` to a long random string. Never use the placeholder in
  production.

### System dependency: Tesseract (OCR)

`pytesseract` is only a Python wrapper. It calls the `tesseract` binary, which
must be installed separately on the machine running the backend:

- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: https://github.com/UB-Mannheim/tesseract/wiki

Without it, PDF pages that need OCR (scanned or image-only pages) fail
extraction with a clear error. Native-text PDFs and DOCX files are unaffected.

### First-run model download

The first time the backend embeds text, `fastembed` downloads the
`sentence-transformers/all-MiniLM-L6-v2` model (roughly 80 MB, ONNX format)
and caches it locally. This needs internet access once. After that, embedding
runs fully offline. Run the backend at least once with internet access before
a demo with no wifi.

## Run

```bash
uvicorn app.main:app --reload
```

# If "uvicorn" is not recognized (common on Windows when Scripts isn't on PATH):
python -m uvicorn app.main:app --reload

The API is served at `http://localhost:8000`. Interactive docs are at
`http://localhost:8000/docs`.

## Configuration

All settings live in `app/core/config.py` and are read from environment
variables or `.env`.

| Variable                      | Default                           | Purpose                                   |
| ----------------------------- | --------------------------------- | ----------------------------------------- |
| `APP_NAME`                    | `Legal Document Assistant`        | Shown in `/` and `/health`                |
| `ENV`                         | `development`                     | Environment label                         |
| `DEBUG`                       | `true`                            | Debug flag                                |
| `DATABASE_URL`                | `sqlite:///./app.db`              | SQLite locally, or a `postgresql://…` URL |
| `JWT_SECRET`                  | `changeme_generate_a_real_secret` | Signs access tokens, **change it**        |
| `JWT_ALGORITHM`               | `HS256`                           |                                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                              | Token lifetime                            |
| `GROQ_API_KEY`                | *(empty)*                         | Required for chat and summary             |
| `GROQ_MODEL`                  | `openai/gpt-oss-120b`             | Model used for chat and summary           |
| `GROQ_API_BASE`               | `https://api.groq.com/openai/v1`  | OpenAI-compatible endpoint                |
| `UPLOAD_DIR`                  | `uploads`                         | Where uploaded files are stored           |
| `MAX_UPLOAD_MB`               | `20`                              | Upload size limit                         |

## Database

SQLAlchemy models (`app/models.py`):

- **`users`**: email (unique), hashed password, full name.
- **`documents`**: owner, original and stored filenames, content type, size,
  `status`, `extracted_text`, `error_message`, and the cached `summary` with
  `summarized_at`.
- **`document_chunks`**: one row per chunk, with `chunk_index`, `text`, and
  `embedding` (a JSON-encoded list of 384 floats in a TEXT column).
- **`chat_messages`**: per-document conversation history (`role` is `user`
  or `assistant`).

Tables are created on startup via `Base.metadata.create_all`. **There are no
migrations.** If the schema changes, delete `app.db` and let the server
recreate it (this wipes data). On Postgres, drop and recreate the affected
tables.

Postgres works by setting `DATABASE_URL`; `psycopg2-binary` is already in
`requirements.txt`.

## API reference

| Method | Endpoint                     | Auth | Description                                         |
| ------ | ---------------------------- | ---- | --------------------------------------------------- |
| GET    | `/`                          | No   | Simple welcome message                              |
| GET    | `/health`                    | No   | Confirms the server is up and the DB is reachable   |
| POST   | `/auth/register`             | No   | Create an account (email, password, optional name)  |
| POST   | `/auth/login`                | No   | Returns `{access_token, token_type}`                |
| GET    | `/auth/me`                   | Yes  | Current user                                        |
| POST   | `/documents/upload`          | Yes  | Upload PDF/DOCX; processing starts in the background|
| GET    | `/documents`                 | Yes  | List your documents, newest first                   |
| GET    | `/documents/{id}`            | Yes  | Document details, status, and summary if cached     |
| GET    | `/documents/{id}/search?q=…` | Yes  | Debug: top matching chunks with similarity scores   |
| POST   | `/documents/{id}/chat`       | Yes  | Ask a question; stores and returns the answer       |
| GET    | `/documents/{id}/chat`       | Yes  | Full chat history for the document                  |
| POST   | `/documents/{id}/summary`    | Yes  | Return cached summary or generate one; `?force=true` regenerates |

Authenticated requests send `Authorization: Bearer <token>`.

**Status codes worth knowing**

- `404`: document doesn't exist **or** belongs to another user (existence is
  never confirmed).
- `409`: document isn't `processed` yet (or has no extractable text).
- `413` / `415` / `400`: file too large, wrong type (only PDF and DOCX), or empty.
- `502`: the Groq call failed, timed out, or no API key is set.

## How processing works

1. **Upload** (`routes/documents.py`): validates type and size, saves the file
   under a UUID filename, creates a `Document` row with status `uploaded`, and
   schedules a background task.
2. **Extraction** (`services/extraction.py`): sets status `processing`. PDFs are
   read with PyMuPDF; any page with fewer than 20 characters of native text is
   rendered at 2x and OCR'd with pytesseract. DOCX files are read with
   python-docx, including table cells.
3. **Chunking** (`services/chunking.py`): splits on paragraph breaks and packs
   paragraphs into ~1000-character chunks with 150 characters of overlap.
   Single paragraphs longer than a chunk are hard-split.
4. **Embedding** (`services/embeddings.py`): `fastembed` runs
   `all-MiniLM-L6-v2` and returns normalized 384-dim vectors. The model loads
   lazily, once per process.
5. **Done:** status becomes `processed`, or `failed` with `error_message`
   (extraction errors and embedding errors are both surfaced).

## How chat and summary work

**Chat** (`services/chat.py`, `services/retrieval.py`)

1. Embed the question and compute cosine similarity against the document's
   stored chunk vectors (numpy, in Python).
2. Take the top 5 chunks and build a system prompt telling the model to answer
   **only** from those excerpts, to say so when the answer isn't there, and to
   explain legal terms in plain language.
3. Send the system prompt, the last 5 turns of history, and the new question to
   Groq (`temperature=0.2`, 30 second timeout).
4. Store both messages and return the answer.

**Summary** (`services/summary.py`)

Uses the document's full `extracted_text` instead of retrieved chunks, because
a summary needs the whole document. Input is truncated to the first 40,000
characters (the model is told when this happens). The result is structured as
an overview, key terms and obligations, and things to watch for, then cached on
the `Document` row so revisits don't re-call the LLM.

## Project layout

```
backend/
├── app/
│   ├── main.py            # App, lifespan (create_all), CORS, /health
│   ├── models.py          # User, Document, DocumentChunk, ChatMessage
│   ├── schemas.py         # Pydantic models
│   ├── database.py        # Engine and session factory
│   ├── deps.py            # get_current_user
│   ├── core/
│   │   ├── config.py      # Settings
│   │   └── security.py    # bcrypt hashing, JWT create/decode
│   ├── routes/
│   │   ├── auth_routes.py
│   │   └── documents.py
│   └── services/
│       ├── extraction.py
│       ├── chunking.py
│       ├── embeddings.py
│       ├── retrieval.py
│       ├── llm.py
│       ├── chat.py
│       └── summary.py
├── requirements.txt
└── .env.example
```

## Deployment notes

- Run with `uvicorn app.main:app --host 0.0.0.0 --port $PORT` on hosts like
  Render. Tesseract must be available in the runtime if you need OCR.
- CORS currently allows all origins (`allow_origins=["*"]`). Restrict it to your
  frontend's origin in production.
- Uploaded files are written to local disk. On hosts with ephemeral
  filesystems they may not survive a restart. Extracted text and chunks are
  stored in the database, so chat and summary keep working.
- The repo's `.github/workflows/keep-alive.yml` pings `/health` every 10
  minutes to keep a free-tier Render instance awake. Update its URL if you
  deploy your own copy.

## Not included

Risky-clause detection (flagging unusual terms with severity labels) is not
implemented. Nothing else depends on it, so it can be added independently.
The similarity search is in-process numpy, which is fine for a few hundred
chunks per document; swap `services/retrieval.py` for pgvector or a vector
store if you need more scale.