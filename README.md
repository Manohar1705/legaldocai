# Legal Document Assistant

Upload a contract (PDF or DOCX), then chat with it or get a plain-language
summary — powered by retrieval-augmented generation over the document's
own text, not general knowledge.

**Stack:** FastAPI + SQLite backend, React + Vite frontend, embeddings via
`sentence-transformers`, chat/summary via Groq (`openai/gpt-oss-120b`).

## Quick start

Two servers, run in separate terminals.

**Backend** (see `backend/README.md` for full details, including the
`tesseract` OCR dependency and Groq API key):

```
cd backend
cp .env.example .env        # then set GROQ_API_KEY in .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (see `frontend/README.md`):

```
cd frontend
cp .env.example .env
npm install
npm run dev
```

Then visit `http://localhost:5173`, register an account, and upload a
document.

## What's included

- Auth: register/login with JWT + bcrypt
- Document upload: PDF and DOCX, stored on disk, tracked in SQLite
- Text extraction: PyMuPDF for native PDF text, OCR fallback via
  pytesseract for scanned pages, python-docx for Word files
- Chunking + embeddings: documents are split into overlapping chunks and
  embedded with `all-MiniLM-L6-v2`
- Similarity search: cosine similarity over stored chunk embeddings
- **Chat** — ask questions about a document; answers are grounded only in
  retrieved excerpts, with the model instructed to say so if an answer
  isn't in the document
- **Summary** — a cached, plain-language summary of the whole document
  (overview, key terms, things to watch for)

Risky-clause detection was scoped as a later step and isn't in this build
— see the note in `backend/README.md`.

## Notes for whoever runs this next

- SQLite has no migrations wired up here — if you pull a version with a
  changed `Document`/`ChatMessage` schema, delete `backend/app.db` and
  let `uvicorn` recreate it (you'll lose any existing test data, which is
  expected in dev).
- The embedding model downloads once from Hugging Face on first use
  (~80MB); do that with real internet access before a demo with no wifi.
- Neither `.env` file is committed — copy the `.env.example` in each
  folder and fill in real values (`GROQ_API_KEY` in particular).
