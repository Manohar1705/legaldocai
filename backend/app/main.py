from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import engine, Base, get_db
from app import models  # noqa: F401 — registers User model on Base before create_all
from app.routes.auth_routes import router as auth_router
from app.routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables for any models registered on Base by the time this runs.
    # Right now there are no models yet (Step 2 adds User) — this just proves
    # the DB file/connection works.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Wide open for local dev between the Vite frontend (5173) and this API (8000).
# Tighten this once you know your deployed frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Confirms the server is up AND the DB connection actually works,
    not just that FastAPI booted.
    """
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "database": "connected",
    }


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} API — see /docs for endpoints"}
