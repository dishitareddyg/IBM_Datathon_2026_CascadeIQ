"""
app/repositories/weather_repository.py
---------------------------------------
In-memory cache for weather observations and warnings with TTL.

Observations are considered stale after TTL_SECONDS and re-fetched
on the next request.  Source is always tagged in each observation dict.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


class WeatherRepository:
    """Simple in-memory weather cache with 5-minute TTL."""

    TTL_SECONDS: int = 300  # 5 minutes

    def __init__(self) -> None:
        self._observations: list[dict] = []
        self._warnings: list[dict] = []
        self._fetched_at: Optional[datetime] = None

    def is_fresh(self) -> bool:
        """Return True if cached data was fetched within the last TTL_SECONDS."""
        if self._fetched_at is None:
            return False
        elapsed = (datetime.now(tz=timezone.utc) - self._fetched_at).total_seconds()
        return elapsed < self.TTL_SECONDS

    def update(self, observations: list[dict], warnings: list[dict]) -> None:
        """Replace cached data and reset the TTL clock."""
        self._observations = list(observations)
        self._warnings = list(warnings)
        self._fetched_at = datetime.now(tz=timezone.utc)

    def get_observations(self) -> list[dict]:
        """Return currently cached rainfall observations."""
        return list(self._observations)

    def get_warnings(self) -> list[dict]:
        """Return currently cached weather warnings."""
        return list(self._warnings)

    @property
    def fetched_at(self) -> Optional[datetime]:
        """Timestamp of the most recent cache refresh, or None."""
        return self._fetched_at


# Singleton for Phase 1
weather_repo = WeatherRepository()
