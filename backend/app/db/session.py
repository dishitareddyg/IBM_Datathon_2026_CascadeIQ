"""
Optional SQLAlchemy 2.x session factory.

Phase 1 runs fully in-memory. When DATABASE_URL is set, an engine is created
so Phase 3 can attach PostgreSQL/PostGIS without rewriting services.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Optional[Engine]:
    global _engine, _SessionLocal
    settings = get_settings()
    if not settings.database_configured:
        return None
    if _engine is None:
        _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_db() -> Generator[Session, None, None]:
    engine = get_engine()
    if engine is None or _SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL is not configured. CascadeIQ Phase 1 operates in-memory."
        )
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
