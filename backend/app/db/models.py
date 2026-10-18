"""
app/db/models.py
----------------
SQLAlchemy ORM models for Phase 3 PostgreSQL/PostGIS persistence.

These models are defined for Phase 3 persistence.
In Phase 1, in-memory repositories are used and these models are not active.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ScenarioRecord(Base):
    """Persists a scenario input JSON blob for later retrieval."""

    __tablename__ = "scenario_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SimulationRecord(Base):
    """Persists a completed simulation result JSON blob."""

    __tablename__ = "simulation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
