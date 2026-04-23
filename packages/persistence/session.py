"""Database session utilities."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db_session() -> Session:
    """Yields DB session for FastAPI dependency."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
