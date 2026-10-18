"""
app/utils/time.py
-----------------
Time / datetime utility functions for CascadeIQ.
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def format_iso8601(dt: datetime) -> str:
    """Format a datetime as an ISO-8601 string (UTC, with 'Z' suffix)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def travel_time_s_to_human(seconds: float) -> str:
    """Convert a duration in seconds to a human-readable string.

    Examples
    --------
    >>> travel_time_s_to_human(323)
    '5m 23s'
    >>> travel_time_s_to_human(3661)
    '1h 1m 1s'
    """
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def compute_simulation_timestamp(
    base_time: datetime,
    step: int,
    step_duration_minutes: int = 15,
) -> datetime:
    """Return the simulated wall-clock time for a given step index.

    Parameters
    ----------
    base_time:
        UTC start time of the simulation.
    step:
        Zero-based step index.
    step_duration_minutes:
        Duration of each step in simulated minutes (default: 15).
    """
    from datetime import timedelta  # local import to avoid circular issues
    return base_time + timedelta(minutes=step * step_duration_minutes)
