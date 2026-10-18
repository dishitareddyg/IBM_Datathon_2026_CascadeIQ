"""
Simulation result dataclasses.

These types capture the outputs of each simulation step: route results, cascade
events, per-step summaries, assignment decisions, and optimisation candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Routing result
# ---------------------------------------------------------------------------

@dataclass
class RouteResult:
    """The result of a shortest-path query between two road-graph nodes."""

    source_node: str
    target_node: str
    path_nodes: list[str]           # ordered list of node_ids
    edge_ids: list[str]             # ordered list of edge_ids traversed
    total_distance_m: float
    total_time_s: float
    is_feasible: bool
    infeasibility_reason: Optional[str] = None

    # ------------------------------------------------------------------
    def total_time_human(self) -> str:
        """Return a human-readable representation, e.g. '4m 32s'."""
        from app.utils.time import travel_time_s_to_human   # local import to avoid cycles
        return travel_time_s_to_human(self.total_time_s)


# ---------------------------------------------------------------------------
# Cascade events & step snapshots
# ---------------------------------------------------------------------------

@dataclass
class CascadeEvent:
    """A discrete event that occurred during a simulation step."""

    step: int
    event_type: str         # 'ROAD_CLOSED' | 'HOSPITAL_OVERLOADED' | 'REQUEST_UNREACHABLE' | 'FACILITY_ISOLATED'
    description: str
    affected_entity_id: str
    severity: float         # 0.0–1.0


@dataclass
class CascadeStep:
    """A full snapshot of the simulation at a single time-step."""

    step_index: int
    timestamp: datetime
    active_disruptions: list[str] = field(default_factory=list)     # edge_ids
    unreachable_requests: list[str] = field(default_factory=list)   # request_ids
    isolated_facilities: list[str] = field(default_factory=list)    # hospital_ids
    hospital_loads: dict[str, float] = field(default_factory=dict)  # hospital_id → load
    cascade_events: list[CascadeEvent] = field(default_factory=list)

    # ------------------------------------------------------------------
    def has_critical_events(self) -> bool:
        """Return True if any cascade event has severity ≥ 0.8."""
        return any(e.severity >= 0.8 for e in self.cascade_events)

    def summary_dict(self) -> dict:
        """Serialisable summary of this step for API responses."""
        return {
            "step_index": self.step_index,
            "timestamp": self.timestamp.isoformat(),
            "active_disruptions_count": len(self.active_disruptions),
            "unreachable_requests_count": len(self.unreachable_requests),
            "isolated_facilities_count": len(self.isolated_facilities),
            "cascade_events_count": len(self.cascade_events),
            "has_critical_events": self.has_critical_events(),
        }


# ---------------------------------------------------------------------------
# Assignment & intervention
# ---------------------------------------------------------------------------

@dataclass
class AssignmentResult:
    """The outcome of assigning an ambulance to an emergency request."""

    ambulance_id: str
    request_id: str
    hospital_id: Optional[str] = None
    route: Optional[RouteResult] = None
    estimated_arrival_s: Optional[float] = None
    is_feasible: bool = True
    reason: str = "OK"

    # ------------------------------------------------------------------
    def estimated_arrival_human(self) -> str:
        """Return human-readable ETA, or 'N/A' when not feasible."""
        if self.estimated_arrival_s is None or not self.is_feasible:
            return "N/A"
        from app.utils.time import travel_time_s_to_human
        return travel_time_s_to_human(self.estimated_arrival_s)


@dataclass
class InterventionCandidate:
    """
    A candidate intervention recommended by the optimiser.

    ``objective_score`` is computed by the optimiser — **lower is better**.
    Feasibility is assessed before inclusion in the candidate list, but
    ``feasible=False`` candidates may still be included for transparency.
    """

    action_id: str
    intervention_type: str      # 'REROUTE' | 'DIVERT' | 'PREPOSITION'
    description: str
    target_ambulance_id: Optional[str] = None
    target_request_id: Optional[str] = None
    target_hospital_id: Optional[str] = None
    new_route: Optional[RouteResult] = None
    feasible: bool = True
    infeasibility_reason: Optional[str] = None
    objective_score: float = 0.0        # lower is better
    response_time_improvement_s: float = 0.0
    hospital_overload_reduction: float = 0.0
    intervention_cost: float = 0.0

    def net_benefit(self) -> float:
        """Simple scalar combining time saving and overload reduction minus cost."""
        return (
            self.response_time_improvement_s * 1.0
            + self.hospital_overload_reduction * 300.0  # weight in seconds-equivalent
            - self.intervention_cost
        )


# ---------------------------------------------------------------------------
# Top-level simulation result (used by repository)
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """
    Complete output of a finished simulation run.

    Stored verbatim in the :class:`~app.repositories.scenario_repository.ScenarioRepository`.
    """

    simulation_id: str
    scenario_id: str
    seed: int
    started_at: datetime
    finished_at: datetime
    steps: list[CascadeStep] = field(default_factory=list)
    assignments: list[AssignmentResult] = field(default_factory=list)
    interventions: list[InterventionCandidate] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def total_steps(self) -> int:
        return len(self.steps)

    def total_unreachable_requests(self) -> int:
        return sum(len(s.unreachable_requests) for s in self.steps)

    def max_hospital_load(self) -> float:
        loads = [
            load
            for step in self.steps
            for load in step.hospital_loads.values()
        ]
        return max(loads, default=0.0)

    def summary(self) -> dict:
        """High-level summary dict for API list endpoints."""
        return {
            "simulation_id": self.simulation_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "total_steps": self.total_steps(),
            "total_unreachable_requests": self.total_unreachable_requests(),
            "max_hospital_load": self.max_hospital_load(),
        }
