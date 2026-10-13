# Legal Document Assistant

Upload a contract (PDF or DOCX), then chat with it or get a plain-language
summary. Answers come from retrieval-augmented generation (RAG) over the
document's own text, not from the model's general knowledge.

**Stack**

| Layer      | Tech                                                                 |
| ---------- | -------------------------------------------------------------------- |
| Backend    | FastAPI, SQLAlchemy, SQLite (local) or PostgreSQL (via `psycopg2`)   |
| Frontend   | React 19, Vite, React Router, Axios, React Markdown                  |
| Extraction | PyMuPDF (native PDFs), pytesseract (OCR for scans), python-docx      |
| Embeddings | `fastembed` (ONNX) running `sentence-transformers/all-MiniLM-L6-v2`  |
| LLM        | Groq API, `openai/gpt-oss-120b` (OpenAI-compatible, plain `httpx`)   |
| Auth       | JWT (`python-jose`) + bcrypt (`passlib`)                             |

## How it works

```
Upload PDF/DOCX
      │
      ▼
Extract text ──(scanned page? OCR)──► Chunk (~1000 chars, 150 overlap)
                                            │
                                            ▼
                              Embed with all-MiniLM-L6-v2 (384-dim)
                                            │
                                            ▼
                         Store chunks + vectors in document_chunks
                                            │
              ┌─────────────────────────────┴───────────────────────┐
              ▼                                                     ▼
   Chat: embed question → cosine similarity           Summary: send full extracted
   → top 5 chunks + last 5 turns → Groq LLM           text (first 40K chars) → Groq LLM
```

Extraction, chunking, and embedding run as a background task after upload,
so the upload response stays fast. A document's `status` moves
`uploaded → processing → processed` (or `failed`, with an error message).

## Features

- **Auth:** register, login, and a protected `/auth/me` endpoint, using JWT and bcrypt.
- **Upload:** PDF and DOCX only, 20 MB limit by default (`MAX_UPLOAD_MB`). Files are stored on disk under UUID names, tracked in the database.
- **Text extraction:** native text via PyMuPDF. Any PDF page with fewer than 20 characters is rendered and OCR'd. DOCX extraction includes table cells.
- **Chunking and embeddings:** paragraph-aware chunks with overlap, embedded locally. No embedding API key is needed.
- **Similarity search:** cosine similarity over stored vectors, computed in numpy. Vectors are stored as JSON in a TEXT column, so no vector extension is required.
- **Chat:** answers are grounded only in the retrieved excerpts. The model is told to say so when the answer isn't in the document. Per-document chat history is persisted and the last 5 turns are sent for follow-up context.
- **Summary:** plain-language overview, key terms and obligations, and things to watch for. It is cached on the document row and can be regenerated with `?force=true` (a Regenerate button in the UI). Very long documents are truncated to the first 40,000 characters, and the model is told.
- **Per-user isolation:** users can only see their own documents. Accessing someone else's returns 404, not 403.
- **Frontend:** document list with live status polling, a chat tab with optimistic sending and markdown rendering, and a summary tab.

## Project structure

```
legaldocai/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, /health
│   │   ├── models.py          # User, Document, DocumentChunk, ChatMessage
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── database.py        # Engine + session (SQLite or Postgres)
│   │   ├── deps.py            # get_current_user dependency
│   │   ├── core/              # config (env settings), JWT/bcrypt helpers
│   │   ├── routes/            # auth_routes.py, documents.py
│   │   └── services/          # extraction, chunking, embeddings,
│   │                          # retrieval, llm, chat, summary
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/             # Login, Register, Dashboard, Documents, DocumentChat
│   │   ├── components/        # Header, AuthShell, ProtectedRoute
│   │   ├── context/           # AuthContext
│   │   └── api/               # Axios client + auth/documents calls
│   └── .env.example
└── .github/workflows/keep-alive.yml
```

## Quick start

You need Python 3.10+, Node.js, and a free [Groq API key](https://console.groq.com/keys).
Run the two servers in separate terminals.

### 1. Install Tesseract (for scanned PDFs)

`pytesseract` is only a wrapper, so the `tesseract` binary must be installed
on the machine running the backend:

- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: https://github.com/UB-Mannheim/tesseract/wiki

Without it, only scanned or image-only PDF pages fail (with a clear error).
Native-text PDFs and DOCX files work fine.

### 2. Backend

```bash
cd backend
cp .env.example .env         # then set GROQ_API_KEY and JWT_SECRET
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`, with interactive docs at `/docs`.

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`, register an account, and upload a document.

## Configuration

**Backend (`backend/.env`)**

| Variable                      | Default                          | Notes                                              |
| ----------------------------- | -------------------------------- | -------------------------------------------------- |
| `GROQ_API_KEY`                | *(empty)*                        | Required for chat and summary                      |
| `JWT_SECRET`                  | `changeme_generate_a_real_secret`| **Change this** before deploying                   |
| `DATABASE_URL`                | `sqlite:///./app.db`             | Use a `postgresql://…` URL for Postgres            |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                             |                                                    |
| `JWT_ALGORITHM`               | `HS256`                          |                                                    |
| `APP_NAME`, `ENV`, `DEBUG`    | see `.env.example`               |                                                    |

Optional settings with defaults in `app/core/config.py`: `UPLOAD_DIR`
(`uploads`), `MAX_UPLOAD_MB` (`20`), `GROQ_MODEL` (`openai/gpt-oss-120b`),
`GROQ_API_BASE`.

**Frontend (`frontend/.env`)**

| Variable       | Default                 | Notes                      |
| -------------- | ----------------------- | -------------------------- |
| `VITE_API_URL` | `http://localhost:8000` | Point at your backend URL  |

## API overview

| Method | Endpoint                      | Description                                        |
| ------ | ----------------------------- | -------------------------------------------------- |
| GET    | `/health`                     | Health check, verifies the DB connection           |
| POST   | `/auth/register`              | Create an account                                  |
| POST   | `/auth/login`                 | Returns a JWT access token                         |
| GET    | `/auth/me`                    | Current user                                       |
| POST   | `/documents/upload`           | Upload a PDF/DOCX (starts background processing)   |
| GET    | `/documents`                  | List your documents                                |
| GET    | `/documents/{id}`             | Document details and status                        |
| GET    | `/documents/{id}/search?q=…`  | Debug endpoint: top matching chunks for a query    |
| POST   | `/documents/{id}/chat`        | Ask a question about the document                  |
| GET    | `/documents/{id}/chat`        | Full chat history for the document                 |
| POST   | `/documents/{id}/summary`     | Get (or generate) the summary; `?force=true` regenerates |

Everything except `/health`, `/auth/register`, and `/auth/login` requires a
`Bearer` token. Chat, search, and summary return `409` until a document's
status is `processed`, and `502` if the Groq call fails.

## Deployment

The backend is set up to run on [Render](https://render.com). Free-tier
services spin down when idle, so `.github/workflows/keep-alive.yml` pings the
backend's `/health` endpoint every 10 minutes. If you deploy your own copy,
update the URL in that workflow to match your service.

For a hosted database, set `DATABASE_URL` to a PostgreSQL connection string
(`psycopg2-binary` is already in `requirements.txt`).

## Notes

- **No migrations.** Tables are created on startup with `create_all`. After
  pulling a version with a changed schema, delete `backend/app.db` and let
  `uvicorn` recreate it. This wipes existing data. On Postgres, drop and
  recreate the affected tables.
- **First-run model download.** `fastembed` downloads the embedding model
  (roughly 80 MB) on first use, then caches it locally. Run the backend once
  with internet access before any offline demo.
- **Secrets.** `.env` files are git-ignored. Copy each `.env.example` and fill
  in real values.
- **CORS is wide open** (`allow_origins=["*"]`) for easy local development.
  Restrict it to your frontend's origin in production.
- **Uploaded files live on local disk** (`backend/uploads/`). On hosts with
  ephemeral filesystems, files may not survive a restart. Extracted text and
  chunks stay in the database, so chat and summary keep working.

## Limitations and roadmap

- **Risky-clause detection** (flagging unusual terms with severity labels) is
  not implemented. Nothing else depends on it, so it can be added on its own.
- Similarity search loads a document's vectors into memory, which is fine for
  a few hundred chunks per document. For much larger scale, swap
  `services/retrieval.py` for pgvector or a dedicated vector store.
- Summaries only cover the first ~40K characters of very long documents.
- This tool explains documents in plain language. It is **not legal advice**.
  Have a qualified lawyer review anything important.

See `backend/README.md` and `frontend/README.md` for more detail on each side.