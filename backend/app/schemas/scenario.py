"""
app/schemas/scenario.py
────────────────────────
Pydantic v2 schemas for scenario configuration and input.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── Road Status Enum ───────────────────────────────────────────────────────────
class RoadStatus(str, Enum):
    """
    Operational state of a road segment.

    OPEN      — Fully passable at normal speed.
    DEGRADED  — Passable at reduced speed due to flooding / damage.
    CLOSED    — Impassable; excluded from routing.
    """

    OPEN = "OPEN"
    DEGRADED = "DEGRADED"
    CLOSED = "CLOSED"


# ── Hospital Input ─────────────────────────────────────────────────────────────
class HospitalInput(_Base):
    """
    Static configuration for a hospital resource in the scenario.

    ``available_beds`` must not exceed ``total_beds``.
    """

    hospital_id: str = Field(..., description="Unique identifier for this hospital.")
    name: str = Field(..., description="Common name of the hospital.")
    lat: float = Field(..., description="Hospital latitude (WGS-84).")
    lon: float = Field(..., description="Hospital longitude (WGS-84).")
    total_beds: int = Field(..., ge=1, description="Total bed capacity.")
    available_beds: int = Field(..., ge=0, description="Beds available at scenario start.")
    icu_beds: int = Field(..., ge=0, description="ICU beds available at scenario start.")

    @model_validator(mode="after")
    def _capacity_check(self) -> "HospitalInput":
        if self.available_beds > self.total_beds:
            raise ValueError(
                f"available_beds ({self.available_beds}) cannot exceed "
                f"total_beds ({self.total_beds})."
            )
        if self.icu_beds > self.available_beds:
            raise ValueError(
                f"icu_beds ({self.icu_beds}) cannot exceed "
                f"available_beds ({self.available_beds})."
            )
        return self


# ── Ambulance Input ────────────────────────────────────────────────────────────
class AmbulanceInput(_Base):
    """
    State of a single ambulance unit at the start of the scenario.
    """

    ambulance_id: str = Field(..., description="Unique identifier for this ambulance.")
    lat: float = Field(..., description="Current ambulance latitude (WGS-84).")
    lon: float = Field(..., description="Current ambulance longitude (WGS-84).")
    is_available: bool = Field(
        default=True,
        description="False if the ambulance is already dispatched at scenario start.",
    )
    assigned_request_id: str | None = Field(
        default=None,
        description="ID of the emergency request currently being served (if any).",
    )

    @model_validator(mode="after")
    def _assignment_consistency(self) -> "AmbulanceInput":
        if not self.is_available and self.assigned_request_id is None:
            raise ValueError(
                "An unavailable ambulance must have an 'assigned_request_id'."
            )
        if self.is_available and self.assigned_request_id is not None:
            raise ValueError(
                "An available ambulance must not have an 'assigned_request_id'."
            )
        return self


# ── Emergency Request Input ────────────────────────────────────────────────────
class EmergencyRequestInput(_Base):
    """
    A single emergency call received at the start of the scenario.
    """

    request_id: str = Field(..., description="Unique identifier for this emergency request.")
    origin_lat: float = Field(..., description="Latitude of the emergency location (WGS-84).")
    origin_lon: float = Field(..., description="Longitude of the emergency location (WGS-84).")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Clinical triage priority of the request.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp at which the emergency call was received.",
    )


# ── Road Disruption ────────────────────────────────────────────────────────────
class RoadDisruption(_Base):
    """
    A flood-driven disruption applied to a specific road edge.

    ``severity`` (0–1) modulates the speed penalty when status is DEGRADED.
    ``confidence`` (0–1) indicates how certain the disruption estimate is;
    values below 0.5 are treated as low-confidence by the simulator.
    ``estimated_by`` records whether the disruption was inferred from a
    model or provided as ground truth.
    """

    edge_id: str = Field(
        ...,
        description="Composite edge identifier '{source_node}-{target_node}'.",
    )
    status: RoadStatus = Field(..., description="New operational status for this edge.")
    severity: float = Field(
        ..., ge=0.0, le=1.0,
        description=(
            "Disruption severity [0, 1]. "
            "0 = no impact (only valid when status=OPEN), "
            "1 = maximum degradation."
        ),
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence in this disruption estimate [0, 1].",
    )
    cause: str = Field(
        ...,
        description="Free-text description of the disruption cause (e.g., 'Flash flood — Koramangala').",
    )
    estimated_by: str = Field(
        ...,
        description="Source of the disruption estimate (e.g., 'flood_risk_model_v1', 'manual').",
    )

    @field_validator("severity")
    @classmethod
    def _severity_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("severity must be in [0, 1].")
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be in [0, 1].")
        return v


# ── Scenario Input ─────────────────────────────────────────────────────────────
class ScenarioInput(_Base):
    """
    Complete description of a simulation scenario.

    The simulator will apply ``road_disruptions``, then run the cascade
    propagation for ``simulation_steps`` discrete steps, producing a
    ``SimulationResult``.
    """

    scenario_id: str = Field(
        ...,
        description="Human-readable name for this scenario (e.g., 'flood_2024_koramangala').",
    )
    seed: int = Field(
        default=42,
        description="Random seed for reproducible synthetic data generation.",
    )
    hospitals: list[HospitalInput] = Field(
        ..., min_length=1,
        description="Hospital resources available in this scenario.",
    )
    ambulances: list[AmbulanceInput] = Field(
        ..., min_length=1,
        description="Ambulance fleet available at scenario start.",
    )
    emergency_requests: list[EmergencyRequestInput] = Field(
        default_factory=list,
        description="Emergency calls to be triaged and dispatched during the simulation.",
    )
    road_disruptions: list[RoadDisruption] = Field(
        default_factory=list,
        description="Flood-driven road disruptions to be applied before the simulation begins.",
    )
    simulation_steps: int = Field(
        default=10, ge=1, le=50,
        description="Number of discrete time steps to simulate (each step = 5 simulated minutes).",
    )
    weather_mode: Literal["synthetic", "historical", "live"] = Field(
        default="synthetic",
        description=(
            "Weather data source. 'live' requires a valid IMD_API_KEY in the environment; "
            "'historical' uses bundled archive data; 'synthetic' generates random values."
        ),
    )

    @model_validator(mode="after")
    def _unique_ids(self) -> "ScenarioInput":
        h_ids = [h.hospital_id for h in self.hospitals]
        if len(h_ids) != len(set(h_ids)):
            raise ValueError("Duplicate hospital_id values found in 'hospitals'.")

        a_ids = [a.ambulance_id for a in self.ambulances]
        if len(a_ids) != len(set(a_ids)):
            raise ValueError("Duplicate ambulance_id values found in 'ambulances'.")

        r_ids = [r.request_id for r in self.emergency_requests]
        if len(r_ids) != len(set(r_ids)):
            raise ValueError("Duplicate request_id values found in 'emergency_requests'.")

        return self


# ── Bundled Scenario Config ────────────────────────────────────────────────────
class ScenarioConfig(_Base):
    """
    Catalogue entry for a bundled / pre-built scenario shipped with the
    CascadeIQ backend.  Used by GET /api/v1/scenarios to list available
    scenarios without requiring the client to supply full ScenarioInput JSON.
    """

    scenario_id: str = Field(..., description="Unique scenario identifier (slug).")
    display_name: str = Field(..., description="Human-readable scenario name.")
    description: str = Field(..., description="One-paragraph description of the scenario.")
    weather_mode: Literal["synthetic", "historical", "live"] = Field(default="synthetic")
    default_simulation_steps: int = Field(default=10, ge=1, le=50)
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags for filtering (e.g., ['flood', 'koramangala', 'high-severity']).",
    )
