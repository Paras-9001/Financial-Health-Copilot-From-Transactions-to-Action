import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/fhc_test")
os.environ.setdefault("JWT_SECRET", "test-only-secret-" * 4)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.rate_limit import limiter
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture
def db_engine():
    # Fast, isolated auth tests. Full PostgreSQL migration checks are separate.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(db_engine):
    def session_override():
        with Session(db_engine) as db:
            yield db

    app.dependency_overrides[get_db] = session_override
    limiter.entries.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.entries.clear()


@pytest.fixture
def signup_payload():
    return {"email": "learner@example.com", "password": "correct horse battery", "name": "Learner"}
