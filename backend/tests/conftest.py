"""
tests/conftest.py

Pytest fixtures shared across all test modules.

The 'client' fixture gives each test an isolated FastAPI TestClient backed
by a fresh in-memory SQLite database. No external PostgreSQL required to
run the test suite — each test starts with empty tables and is fully
independent of every other test.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db


@pytest.fixture
def client():
    """
    Provides a TestClient with a fresh SQLite in-memory database per test.

    How it works:
      1. Creates a brand-new SQLite in-memory database using StaticPool.
      2. Tells SQLAlchemy to create all tables in that database.
      3. Overrides FastAPI's get_db dependency so every route uses this
         test database instead of the real PostgreSQL one.
      4. Yields the TestClient — the test runs here.
      5. After the test, drops all tables and clears the override.

    Why StaticPool?
      sqlite:///:memory: gives each NEW connection its own empty database.
      Without StaticPool, SQLAlchemy's connection pool may open a second
      connection for a route handler — that second connection would see a
      completely empty database with no tables, causing OperationalError.
      StaticPool forces every checkout to reuse the SAME single connection,
      so all code (conftest setup, route handlers, teardown) shares one
      in-memory database and its tables are always visible.
    """
    # Step 1: single shared in-memory SQLite connection for this test
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    # Step 2: create all tables (Goal, TaskChunk, StatusHistory)
    Base.metadata.create_all(bind=engine)

    # Step 3: override get_db so routes use the test DB
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Step 4: give the TestClient to the test
    # The 'with' block triggers FastAPI's lifespan (startup/shutdown events)
    with TestClient(app) as test_client:
        yield test_client

    # Step 5: cleanup — clear dependency override and drop all tables
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
