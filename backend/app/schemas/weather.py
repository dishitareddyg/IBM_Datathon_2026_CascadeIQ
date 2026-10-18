"""
app/schemas/weather.py
───────────────────────
Pydantic v2 schemas for weather observations and warnings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import BoundingBox


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── WeatherSource Enum ─────────────────────────────────────────────────────────
class WeatherSource(str, Enum):
    """
    Identifies the provenance of a weather datum.

    IMD        — Live data from the India Meteorological Department API.
    SYNTHETIC  — Randomly generated values for simulation / testing.
    HISTORICAL — Replayed from a historical archive (e.g., IMD CSV exports).
    """

    IMD = "IMD"
    SYNTHETIC = "SYNTHETIC"
    HISTORICAL = "HISTORICAL"


# ── Rainfall Observation ───────────────────────────────────────────────────────
class RainfallObservation(_Base):
    """
    A single rainfall measurement from one monitoring station.

    ``rainfall_mm_1h`` is the accumulated depth in the past hour;
    ``rainfall_mm_24h`` is the rolling 24-hour accumulation used for
    flood-risk thresholding.
    """

    station_id: str = Field(..., description="Unique identifier for the monitoring station.")
    lat: float = Field(..., description="Station latitude (WGS-84).")
    lon: float = Field(..., description="Station longitude (WGS-84).")
    rainfall_mm_1h: float = Field(
        ..., ge=0.0,
        description="Accumulated rainfall in the past 1 hour (mm).",
    )
    rainfall_mm_24h: float = Field(
        ..., ge=0.0,
        description="Accumulated rainfall in the past 24 hours (mm).",
    )
    observed_at: datetime = Field(
        ...,
        description="UTC timestamp of the observation.",
    )
    source: WeatherSource = Field(
        default=WeatherSource.SYNTHETIC,
        description="Provenance of this observation.",
    )


# ── Weather Warning ────────────────────────────────────────────────────────────
class WeatherWarning(_Base):
    """
    A meteorological warning issued for the study area.

    Severity levels follow IMD's colour-coded warning system:
    WATCH → WARNING → SEVERE → EXTREME.
    """

    warning_id: str = Field(..., description="Unique warning identifier.")
    warning_type: str = Field(
        ...,
        description="Category of warning (e.g., 'HEAVY_RAIN', 'THUNDERSTORM', 'FLOOD').",
    )
    severity: Literal["WATCH", "WARNING", "SEVERE", "EXTREME"] = Field(
        ...,
        description="IMD-aligned severity colour code.",
    )
    description: str = Field(
        ...,
        description="Plain-language description of the hazard and recommended precautions.",
    )
    issued_at: datetime = Field(..., description="UTC time at which this warning was issued.")
    valid_until: datetime = Field(
        ...,
        description="UTC time until which the warning remains in effect.",
    )
    affected_area: BoundingBox | None = Field(
        default=None,
        description="Approximate geographic footprint of the warning. "
                    "None implies the entire study district.",
    )
    source: WeatherSource = Field(
        default=WeatherSource.SYNTHETIC,
        description="Provenance of this warning.",
    )

    @model_validator(mode="after")
    def _validity_check(self) -> "WeatherWarning":
        if self.valid_until <= self.issued_at:
            raise ValueError("'valid_until' must be strictly after 'issued_at'.")
        return self


# ── Aggregated Weather Status ──────────────────────────────────────────────────
class WeatherStatus(_Base):
    """
    Aggregated weather state for the study area returned by GET /api/v1/weather/status.

    ``disclaimer`` must always be shown in the UI to avoid misrepresenting
    simulated values as real IMD observations.
    """

    current_observations: list[RainfallObservation] = Field(
        default_factory=list,
        description="Rainfall observations from all available stations.",
    )
    active_warnings: list[WeatherWarning] = Field(
        default_factory=list,
        description="Currently active meteorological warnings for the study area.",
    )
    data_freshness: datetime = Field(
        ...,
        description="UTC timestamp of the most recent underlying data point.",
    )
    disclaimer: str = Field(
        default=(
            "⚠️  Weather data shown here is SIMULATED for research and educational purposes. "
            "It does NOT represent actual IMD observations. "
            "Do not use for real emergency decision-making."
        ),
        description="Mandatory disclaimer that must be displayed alongside all weather data.",
    )
