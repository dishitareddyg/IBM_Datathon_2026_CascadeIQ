"""
app/schemas/common.py
──────────────────────
Shared Pydantic v2 base schemas used across the CascadeIQ API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ── Bengaluru Urban geographic bounds ─────────────────────────────────────────
# Approximate bounding box for Bengaluru Urban district, Karnataka, India.
_BLR_LAT_MIN: float = 12.7
_BLR_LAT_MAX: float = 13.3
_BLR_LON_MIN: float = 77.2
_BLR_LON_MAX: float = 77.9

T = TypeVar("T")


# ── Base model config ──────────────────────────────────────────────────────────
class _Base(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        frozen=False,
    )


# ── Coordinate ─────────────────────────────────────────────────────────────────
class Coordinate(_Base):
    """
    A single geographic point expressed in WGS-84 (EPSG:4326).

    Validated to lie within the approximate bounds of Bengaluru Urban
    district (~12.7–13.3°N, 77.2–77.9°E).
    """

    lat: float = Field(
        ...,
        ge=_BLR_LAT_MIN,
        le=_BLR_LAT_MAX,
        description="Latitude in decimal degrees (WGS-84). Must be within Bengaluru Urban bounds.",
    )
    lon: float = Field(
        ...,
        ge=_BLR_LON_MIN,
        le=_BLR_LON_MAX,
        description="Longitude in decimal degrees (WGS-84). Must be within Bengaluru Urban bounds.",
    )

    @model_validator(mode="after")
    def _bounds_check(self) -> "Coordinate":
        if not (_BLR_LAT_MIN <= self.lat <= _BLR_LAT_MAX):
            raise ValueError(
                f"Latitude {self.lat} is outside Bengaluru Urban bounds "
                f"[{_BLR_LAT_MIN}, {_BLR_LAT_MAX}]."
            )
        if not (_BLR_LON_MIN <= self.lon <= _BLR_LON_MAX):
            raise ValueError(
                f"Longitude {self.lon} is outside Bengaluru Urban bounds "
                f"[{_BLR_LON_MIN}, {_BLR_LON_MAX}]."
            )
        return self


# ── BoundingBox ────────────────────────────────────────────────────────────────
class BoundingBox(_Base):
    """
    An axis-aligned geographic bounding box in WGS-84.
    min values must be strictly less than max values.
    """

    min_lat: float = Field(..., description="Southern latitude bound (degrees).")
    min_lon: float = Field(..., description="Western longitude bound (degrees).")
    max_lat: float = Field(..., description="Northern latitude bound (degrees).")
    max_lon: float = Field(..., description="Eastern longitude bound (degrees).")

    @model_validator(mode="after")
    def _order_check(self) -> "BoundingBox":
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat must be strictly less than max_lat.")
        if self.min_lon >= self.max_lon:
            raise ValueError("min_lon must be strictly less than max_lon.")
        return self


# ── TimeRange ──────────────────────────────────────────────────────────────────
class TimeRange(_Base):
    """
    A closed time interval [start, end].
    Both datetimes should be timezone-aware (UTC preferred).
    """

    start: datetime = Field(..., description="Interval start (inclusive).")
    end: datetime = Field(..., description="Interval end (inclusive).")

    @model_validator(mode="after")
    def _order_check(self) -> "TimeRange":
        if self.start >= self.end:
            raise ValueError("'start' must be strictly before 'end'.")
        return self


# ── Generic Success Response Wrapper ──────────────────────────────────────────
class SuccessResponse(_Base, Generic[T]):
    """
    Generic API envelope returned for all successful responses.

    Attributes
    ----------
    data        : The actual response payload (typed by the caller).
    metadata    : Optional free-form dict for pagination cursors, counts, etc.
    generated_at: UTC timestamp at which the response was assembled.
    """

    data: T
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp at which this response was assembled.",
    )


# ── Error Response ─────────────────────────────────────────────────────────────
class ErrorResponse(_Base):
    """
    Structured error body returned for all 4xx / 5xx responses.

    Example
    -------
    {
        "error":   "GRAPH_NOT_LOADED",
        "message": "The road-network graph has not been initialised.",
        "detail":  {}
    }
    """

    error: str = Field(..., description="Machine-readable error code (SCREAMING_SNAKE_CASE).")
    message: str = Field(..., description="Human-readable description of the error.")
    detail: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured context (field names, IDs, etc.).",
    )


# ── Pagination ─────────────────────────────────────────────────────────────────
class PaginationParams(_Base):
    """
    Query-parameter model for paginated list endpoints.
    Designed to be used as a FastAPI dependency.
    """

    page: int = Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = Field(
        default=50, ge=1, le=500,
        description="Number of items per page (max 500).",
    )

    @property
    def offset(self) -> int:
        """Zero-based offset into a result set."""
        return (self.page - 1) * self.page_size
