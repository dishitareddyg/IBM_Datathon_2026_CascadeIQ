"""
app/schemas/simulation.py
──────────────────────────
Pydantic v2 schemas representing the output of a cascade simulation run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── Route Segment ──────────────────────────────────────────────────────────────
class RouteSegment(_Base):
    """
    A computed route for an ambulance between two points.

    ``is_feasible`` is False when no path exists in the post-disruption graph;
    in that case ``edge_ids`` will be empty and the distances will be 0.
    """

    edge_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of edge identifiers traversed on this route.",
    )
    total_distance_m: float = Field(
        default=0.0, ge=0.0,
        description="Total route distance in metres.",
    )
    total_time_s: float = Field(
        default=0.0, ge=0.0,
        description="Estimated travel time in seconds (including speed degradation).",
    )
    is_feasible: bool = Field(
        ...,
        description="True if a valid path was found; False if origin/destination are disconnected.",
    )


# ── Ambulance Assignment ───────────────────────────────────────────────────────
class AmbulanceAssignment(_Base):
    """
    The dispatch decision made for one ambulance in a given simulation step.
    """

    ambulance_id: str = Field(..., description="Identifier of the dispatched ambulance.")
    request_id: str = Field(..., description="Identifier of the emergency request being served.")
    hospital_id: str | None = Field(default=None, description="Identifier of the receiving hospital.")
    route: RouteSegment = Field(..., description="Computed route from the emergency origin to the hospital.")
    estimated_arrival_s: float = Field(
        ..., ge=0.0,
        description="Estimated seconds from dispatch to hospital arrival.",
    )


# ── Cascade Step ───────────────────────────────────────────────────────────────
class CascadeEventSchema(_Base):
    """A single computed cascade event (simulated, not an observed incident)."""

    step_index: int = Field(..., ge=0)
    event_type: str = Field(..., description="ROAD_DEGRADED | ROAD_CLOSED | HOSPITAL_OVERLOADED | REQUEST_UNREACHABLE | FACILITY_ISOLATED | ASSIGNMENT")
    description: str
    affected_entity_id: str
    severity: float = Field(..., ge=0.0, le=1.0)
    provenance: str = Field(
        default="simulated",
        description="observed | forecast | inferred | synthetic | scenario | simulated",
    )


class CascadeStep(_Base):
    """
    The state of the simulation at a single discrete time step.

    Each step represents 5 simulated minutes of real-world time.
    ``cascade_events`` is a human-readable list of notable events that
    occurred during this step (e.g., 'Edge X-Y transitioned OPEN → CLOSED').
    """

    step_index: int = Field(..., ge=0, description="Zero-based index of this simulation step.")
    timestamp: datetime = Field(
        ...,
        description="Simulated wall-clock UTC time at the start of this step.",
    )
    active_disruptions: list[str] = Field(
        default_factory=list,
        description="Edge IDs that are currently DEGRADED or CLOSED at this step.",
    )
    unreachable_requests: list[str] = Field(
        default_factory=list,
        description="Request IDs for which no ambulance can reach the origin at this step.",
    )
    isolated_facilities: list[str] = Field(
        default_factory=list,
        description="Hospital IDs that are unreachable from the general road network at this step.",
    )
    hospital_loads: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Mapping of hospital_id → occupancy ratio [0, 1]. "
            "Values > 1.0 indicate overload (more patients than available beds)."
        ),
    )
    cascade_events: list[CascadeEventSchema] = Field(
        default_factory=list,
        description="Ordered list of computed cascade events for this step.",
    )


# ── Simulation Result ──────────────────────────────────────────────────────────
class SimulationResult(_Base):
    """
    Complete output of a CascadeIQ simulation run.

    ``disclaimer`` must always be surfaced in the user interface.
    ``status`` transitions:  PENDING → RUNNING → COMPLETED | FAILED.
    """

    simulation_id: str = Field(
        ...,
        description="UUID identifying this specific simulation run.",
    )
    scenario_id: str = Field(
        ...,
        description="Scenario that was simulated (references ScenarioInput.scenario_id).",
    )
    seed: int = Field(..., description="Random seed used for this run.")
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"] = Field(
        ...,
        description="Lifecycle state of the simulation.",
    )
    steps: list[CascadeStep] = Field(
        default_factory=list,
        description="Ordered sequence of cascade steps produced by the simulation.",
    )
    final_assignments: list[AmbulanceAssignment] = Field(
        default_factory=list,
        description="Ambulance dispatch assignments determined at the final step.",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp at which the simulation was submitted.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp at which the simulation finished (None if still running).",
    )
    disclaimer: str = Field(
        default=(
            "⚠️  Results are generated by a SIMULATION MODEL for research and educational "
            "purposes only. They do NOT represent actual emergency-response outcomes. "
            "Do not use for real-world disaster management decisions."
        ),
        description="Mandatory disclaimer to be displayed alongside all simulation results.",
    )
