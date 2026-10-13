# Frontend: Legal Document Assistant

React + Vite single-page app for the Legal Document Assistant. It talks to the
FastAPI backend in `../backend`.

**Stack:** React 19, Vite 5, React Router 7, Axios, React Markdown, oxlint.

## Setup

```bash
cp .env.example .env
npm install
```

`VITE_API_URL` in `.env` must point at the backend. The default,
`http://localhost:8000`, matches the backend's default `uvicorn` port. For a
deployed backend, set it to that URL (for example your Render service) before
building.

## Scripts

| Command           | What it does                                  |
| ----------------- | --------------------------------------------- |
| `npm run dev`     | Start the dev server at `http://localhost:5173` |
| `npm run build`   | Production bundle in `dist/`                  |
| `npm run preview` | Serve the production build locally            |
| `npm run lint`    | Lint with oxlint                              |

The backend must be running separately (see `../backend/README.md`) for
anything past the login screen to work.

## Pages

| Route            | Page            | Description                                                         |
| ---------------- | --------------- | ------------------------------------------------------------------- |
| `/`              |                 | Redirects to `/dashboard`                                           |
| `/login`         | `Login`         | Sign in                                                             |
| `/register`      | `Register`      | Create an account                                                   |
| `/dashboard`     | `Dashboard`     | Landing page after login                                            |
| `/documents`     | `Documents`     | Upload a PDF/DOCX and see all documents with status badges          |
| `/documents/:id` | `DocumentChat`  | Chat and Summary tabs for a processed document                      |

All routes except `/login` and `/register` are wrapped in `ProtectedRoute`,
which sends signed-out users to the login page.

## Features

- **Auth:** JWT-based. The token is stored in `localStorage` and attached to
  every request by an Axios interceptor. A `401` response clears the token so
  the app falls back to the signed-out state instead of looping on failed
  requests.
- **Upload and status:** upload PDF or DOCX files from the Documents page.
  Status badges move through `uploaded → processing → processed` (or
  `failed`). While any document is still in progress, the page polls the
  backend in the background so badges update without a manual refresh.
- **Chat tab:** ask questions about a processed document. Messages are sent
  optimistically, answers render as Markdown, and the full history is loaded
  from the backend. Documents that aren't ready show a "still processing"
  state instead of the chat box.
- **Summary tab:** the summary is fetched lazily the first time the tab is
  opened and rendered as Markdown. A **Regenerate** button forces a fresh
  summary. Tab state is kept separate, so switching tabs doesn't clobber
  chat or summary errors and loading states.

## Project layout

```
frontend/
├── src/
│   ├── main.jsx            # Entry point
│   ├── App.jsx             # Router and route table
│   ├── index.css           # Global styles
│   ├── api/
│   │   ├── client.js       # Axios instance, auth header, 401 handling
│   │   ├── auth.js         # register / login / me
│   │   └── documents.js    # list, get, upload, chat, summary
│   ├── context/
│   │   └── AuthContext.jsx # Current user and login/logout state
│   ├── components/
│   │   ├── Header.jsx
│   │   ├── AuthShell.jsx   # Shared layout for login/register
│   │   └── ProtectedRoute.jsx
│   └── pages/
│       ├── Login.jsx
│       ├── Register.jsx
│       ├── Dashboard.jsx
│       ├── Documents.jsx
│       └── DocumentChat.jsx
├── public/                 # favicon and icons
├── .env.example
└── vite.config.js
```

## Deployment notes

- `npm run build` produces a static bundle in `dist/` that any static host can
  serve (Netlify, Vercel, Render Static Sites, and so on).
- `VITE_API_URL` is baked in at build time, so rebuild after changing it.
- Because this is a client-side routed app, configure the host to fall back to
  `index.html` for unknown paths so direct links like `/documents/3` work.
- The backend currently allows all CORS origins. Once you know your deployed
  frontend URL, restrict the backend's CORS to it.