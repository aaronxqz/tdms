"""
db/session.py

Creates the SQLAlchemy engine (the actual TCP connection to PostgreSQL)
and a SessionLocal factory. Each API request calls get_db() which yields
a fresh session and guarantees it is closed after the request finishes —
even if an exception was raised.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# The engine is the connection pool — created once at startup
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # checks connection is alive before using it
)

# SessionLocal is a factory: calling SessionLocal() gives you a new session
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # we manually commit so we control when data is saved
    autoflush=False,
)


def get_db():
    """
    FastAPI dependency — inject this into any route that needs DB access.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...

    The 'finally' block ensures the session is always closed,
    even if an exception is raised mid-request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()