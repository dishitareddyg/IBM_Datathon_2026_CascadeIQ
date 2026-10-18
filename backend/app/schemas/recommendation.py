"""
app/schemas/recommendation.py
───────────────────────────────
Pydantic v2 schemas for the recommendation / intervention engine.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.simulation import RouteSegment


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── Intervention Type Enum ─────────────────────────────────────────────────────
class InterventionType(str, Enum):
    """
    Category of decision-support intervention recommended by CascadeIQ.

    REROUTE     — Direct an in-transit ambulance to take an alternative road path.
    DIVERT      — Redirect a patient to a different hospital than originally planned.
    PREPOSITION — Move an idle ambulance to a strategic staging point ahead of demand.
    """

    REROUTE = "REROUTE"
    DIVERT = "DIVERT"
    PREPOSITION = "PREPOSITION"


# ── Intervention Action ────────────────────────────────────────────────────────
class InterventionAction(_Base):
    """
    A single ranked intervention recommended for a simulation run.

    If ``feasible`` is False, ``infeasibility_reason`` explains why the
    action cannot currently be executed and the action should be surfaced
    in the UI with a warning rather than a call-to-action button.
    """

    action_id: str = Field(..., description="Unique identifier for this intervention action.")
    type: InterventionType = Field(..., description="Category of intervention.")
    description: str = Field(
        ...,
        description="Plain-language description of the recommended action.",
    )
    target_ambulance_id: str | None = Field(
        default=None,
        description="Ambulance to be repositioned or rerouted (None for PREPOSITION without assignment).",
    )
    target_request_id: str | None = Field(
        default=None,
        description="Emergency request affected by this intervention.",
    )
    target_hospital_id: str | None = Field(
        default=None,
        description="Destination hospital for DIVERT interventions.",
    )
    new_route: RouteSegment | None = Field(
        default=None,
        description="Proposed new route if the intervention involves physical re-routing.",
    )
    feasible: bool = Field(
        ...,
        description="True if the intervention can be applied under current network constraints.",
    )
    infeasibility_reason: str | None = Field(
        default=None,
        description="Human-readable explanation when feasible=False.",
    )
    objective_score: float | None = Field(
        default=None,
        description="Composite objective value (lower is better). None when infeasible.",
    )
    response_time_s: float | None = Field(default=None, ge=0.0)
    hospital_overload: float | None = Field(default=None, ge=0.0)
    intervention_cost: float = Field(default=0.0, ge=0.0)


# ── Recommendation Request ─────────────────────────────────────────────────────
class RecommendationRequest(_Base):
    """
    Parameters for the GET /api/v1/recommend endpoint.
    """

    simulation_id: str = Field(
        ...,
        description="ID of a previously completed simulation to generate recommendations for.",
    )
    objective_lambda: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="λ — weight for the coverage / response-time term in the objective function.",
    )
    objective_mu: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="μ — weight for the cascade-isolation penalty in the objective function.",
    )
    max_recommendations: int = Field(
        default=5, ge=1, le=50,
        description="Maximum number of intervention actions to return (ranked by objective score).",
    )

    @field_validator("objective_lambda", "objective_mu")
    @classmethod
    def _weight_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Objective weights must be in [0, 1].")
        return v


# ── Recommendation Result ──────────────────────────────────────────────────────
class RecommendationResult(_Base):
    """
    Ranked list of intervention actions returned by the recommendation engine.

    ``objective_scores`` maps action_id → composite objective score so that
    clients can display the ranking rationale.
    ``method_note`` describes the optimisation approach used (e.g.,
    'Greedy heuristic with shortest-path re-evaluation').
    """

    simulation_id: str = Field(..., description="Simulation ID this recommendation was derived from.")
    ranked_interventions: list[InterventionAction] = Field(
        default_factory=list,
        description="Interventions ordered from highest to lowest objective score.",
    )
    objective_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of action_id → composite objective score.",
    )
    computation_latency_ms: float = Field(
        ..., ge=0.0,
        description="Wall-clock time taken by the recommendation engine (milliseconds).",
    )
    method_note: str = Field(
        default="Greedy heuristic with Dijkstra re-evaluation on post-disruption graph.",
        description="Plain-language description of the optimisation method used.",
    )
