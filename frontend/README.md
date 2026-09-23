# Frontend — Legal Document Assistant

React + Vite frontend for the Legal Document Assistant. Talks to the
FastAPI backend in `../backend`.

## Setup

```
cp .env.example .env
npm install
```

`VITE_API_URL` in `.env` should point at the backend (default
`http://localhost:8000` matches the backend's default `uvicorn` port).

## Run

```
npm run dev
```

Visit `http://localhost:5173`. The backend must be running separately
(see `../backend/README.md`) for anything past the login screen to work.

## Build

```
npm run build
```

Outputs a production bundle to `dist/`.

## Pages

- `/login`, `/register` — auth
- `/dashboard` — landing page after login
- `/documents` — upload a PDF/DOCX, see status (uploaded → processing →
  processed/failed)
- `/documents/:id` — Chat and Summary tabs for a processed document
