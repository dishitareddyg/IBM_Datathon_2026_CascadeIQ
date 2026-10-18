"""
Simulation state dataclasses.

These dataclasses represent the mutable state of a single simulation run —
hospitals, ambulances, active emergency requests, road disruptions, and the
top-level SimulationState container.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Priority weight mapping
# ---------------------------------------------------------------------------

PRIORITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 4.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "LOW": 1.0,
}


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Hospital:
    """A hospital or emergency care facility in the simulation."""

    hospital_id: str
    name: str
    lat: float
    lon: float
    nearest_node_id: str   # snapped to road graph
    total_beds: int
    available_beds: int
    icu_beds: int
    current_load: float = 0.0   # 0.0–1.0 — computed from occupied / total_beds
    is_accessible: bool = True   # computed from routing; True by default

    # ------------------------------------------------------------------
    def compute_load(self) -> float:
        """Recalculate *current_load* from bed counts and cache result.

        Returns 1.0 (fully loaded) if *total_beds* is 0 to prevent ZeroDivisionError.
        """
        if self.total_beds <= 0:
            self.current_load = 1.0
        else:
            occupied = self.total_beds - self.available_beds
            self.current_load = max(0.0, min(1.0, occupied / self.total_beds))
        return self.current_load

    def admit_patient(self) -> bool:
        """Decrement available beds if any remain. Returns True on success."""
        if self.available_beds > 0:
            self.available_beds -= 1
            self.compute_load()
            return True
        return False

    def is_overloaded(self, threshold: float = 0.90) -> bool:
        """Return True when occupancy exceeds *threshold* (default 90 %)."""
        return self.compute_load() >= threshold


@dataclass
class Ambulance:
    """A field ambulance unit."""

    ambulance_id: str
    lat: float
    lon: float
    nearest_node_id: str        # snapped to road graph
    is_available: bool = True
    assigned_request_id: Optional[str] = None
    speed_kmh: float = 60.0     # default city ambulance speed

    def assign(self, request_id: str) -> None:
        """Mark this ambulance as dispatched to *request_id*."""
        self.assigned_request_id = request_id
        self.is_available = False

    def release(self) -> None:
        """Mark this ambulance as free."""
        self.assigned_request_id = None
        self.is_available = True


@dataclass
class EmergencyRequest:
    """An incoming emergency that needs an ambulance and hospital."""

    request_id: str
    origin_lat: float
    origin_lon: float
    nearest_node_id: str        # snapped to road graph
    priority: str               # 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority_weight: float = field(init=False)

    def __post_init__(self) -> None:
        self.priority_weight = PRIORITY_WEIGHTS.get(self.priority, 1.0)


@dataclass
class RoadDisruption:
    """A disruption applied to a specific road edge (e.g. flooding, blockage)."""

    edge_id: str
    status: str         # 'DEGRADED' | 'CLOSED'
    severity: float     # 0.0–1.0
    confidence: float   # 0.0–1.0 — how certain the disruption report is
    cause: str          # 'FLOOD' | 'ACCIDENT' | 'DEBRIS' | …
    estimated_by: str   # 'SENSOR' | 'IMD' | 'SYNTHETIC' | 'MANUAL'


# ---------------------------------------------------------------------------
# Top-level simulation state
# ---------------------------------------------------------------------------

@dataclass
class SimulationState:
    """
    Complete mutable state of a simulation run at a given step.

    ``city_graph`` is typed as ``Any`` to avoid a circular import with
    ``app.models.graph``; callers should type-hint it as ``CityGraph``.
    """

    scenario_id: str
    seed: int
    step: int = 0
    hospitals: dict[str, Hospital] = field(default_factory=dict)
    ambulances: dict[str, Ambulance] = field(default_factory=dict)
    requests: dict[str, EmergencyRequest] = field(default_factory=dict)
    disruptions: dict[str, RoadDisruption] = field(default_factory=dict)
    city_graph: Any = None                  # CityGraph reference

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_available_ambulances(self) -> list[Ambulance]:
        """Return all ambulances that are currently free."""
        return [a for a in self.ambulances.values() if a.is_available]

    def get_pending_requests(self) -> list[EmergencyRequest]:
        """Return requests not yet assigned to an ambulance, highest priority first."""
        pending = [
            r for r in self.requests.values()
            if r.request_id not in {
                a.assigned_request_id
                for a in self.ambulances.values()
                if a.assigned_request_id is not None
            }
        ]
        return sorted(pending, key=lambda r: r.priority_weight, reverse=True)

    def apply_disruption(self, disruption: RoadDisruption) -> None:
        """Register a disruption and update the city graph edge status."""
        self.disruptions[disruption.edge_id] = disruption
        if self.city_graph is not None:
            edge = self.city_graph.edges.get(disruption.edge_id)
            if edge is not None:
                edge.status = disruption.status
                edge.flood_risk = max(edge.flood_risk, disruption.severity)
                # Update nx_graph edge attribute too
                parts = disruption.edge_id.split("_")
                if len(parts) >= 2:
                    u, v = parts[0], parts[1]
                    if self.city_graph.nx_graph.has_edge(u, v):
                        self.city_graph.nx_graph[u][v]["status"] = disruption.status

    def advance_step(self) -> None:
        """Increment the simulation step counter."""
        self.step += 1

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"SimulationState(scenario_id='{self.scenario_id}', step={self.step}, "
            f"hospitals={len(self.hospitals)}, ambulances={len(self.ambulances)}, "
            f"requests={len(self.requests)}, disruptions={len(self.disruptions)})"
        )
