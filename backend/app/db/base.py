"""
app/db/base.py
--------------
SQLAlchemy declarative base for ORM models.

Phase 1: Not used in production routes (in-memory repositories only).
Phase 3: Import this base in all ORM model files.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all CascadeIQ ORM models."""
    pass
