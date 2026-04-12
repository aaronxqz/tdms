"""
main.py

FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Register all routers (goals, tasks)
  - Start the APScheduler background job for breach timer checking
  - Create DB tables on first startup (via SQLAlchemy metadata)
  - Enable CORS so the React frontend can call this API

Run with:
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.api import goals, tasks, calendar
from app.db.session import engine, SessionLocal
from app.db.base import Base

# Import all models so SQLAlchemy knows about them when creating tables
from app.models import goal, task_chunk, status_history  # noqa: F401
from app.services.task_service import check_and_apply_breaches


# ---------------------------------------------------------------------------
# Background Scheduler
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()


def breach_check_job():
    """
    Runs every 30 minutes. Opens a DB session, checks for breach violations,
    closes the session. Completely independent of any HTTP request.
    """
    db = SessionLocal()
    try:
        updated = check_and_apply_breaches(db)
        if updated > 0:
            print(f"[Scheduler] Breach check: {updated} chunk(s) moved to BREACH status")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App Lifespan (startup + shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Create all tables that don't exist yet.
    # In production you'd rely solely on Alembic migrations,
    # but this is handy for first-run development.
    # Wrapped in try/except so the app (and tests) still start even if
    # the database is temporarily unavailable — e.g. when pytest uses
    # an in-memory SQLite override via dependency injection.
    try:
        Base.metadata.create_all(bind=engine)
        print("[Startup] Database tables verified/created.")
    except Exception as e:
        print(f"[Startup] Warning: could not reach database at startup: {e}")

    # Start the breach checker — runs every 30 minutes
    scheduler.add_job(breach_check_job, "interval", minutes=30, id="breach_check")
    scheduler.start()
    print("[Startup] Background scheduler started (breach check every 30 min).")

    yield   # <-- application runs here

    # --- SHUTDOWN ---
    scheduler.shutdown(wait=False)
    print("[Shutdown] Scheduler stopped.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Task Distribution and Management System",
    description="API for managing goals, task chunks, urgency, and lifecycle status.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the React dev server (localhost:5173) to call this API.
# In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(calendar.router)


# ---------------------------------------------------------------------------
# Health check — useful to verify the server is alive
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "TDMS API is running"}
