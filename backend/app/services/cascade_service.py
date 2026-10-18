"""Step-wise cascade propagation on a copied city graph."""

from __future__ import annotations

from datetime import datetime

from app.core.config import get_settings
from app.models.entities import AssignmentResult, CascadeEvent, CascadeStep
from app.models.graph import CityGraph
from app.models.scenario import Hospital, SimulationState
from app.services.routing_service import routing_service
from app.utils.time import compute_simulation_timestamp


def _event(step: int, event_type: str, description: str, entity_id: str, severity: float, provenance: str) -> CascadeEvent:
    return CascadeEvent(
        step=step,
        event_type=event_type,
        description=description,
        affected_entity_id=entity_id,
        severity=severity,
        # CascadeEvent dataclass may not have provenance; stored in description when needed
    )


class CascadeService:
    def isolate_facilities(self, graph: CityGraph, hospitals: dict[str, Hospital], probe_nodes: list[str]) -> list[str]:
        isolated: list[str] = []
        for hospital in hospitals.values():
            reachable = False
            for probe in probe_nodes:
                if routing_service.is_reachable(graph, probe, hospital.nearest_node_id):
                    reachable = True
                    break
            hospital.is_accessible = reachable
            if not reachable:
                isolated.append(hospital.hospital_id)
        return isolated

    def assign_requests(
        self,
        state: SimulationState,
        *,
        capacity_aware: bool,
        overload_threshold: float,
    ) -> list[AssignmentResult]:
        """
        Greedy assignment: pending requests by priority, then available ambulances.

        baseline (capacity_aware=False): nearest reachable hospital among those with remaining beds.
        cascadeiq (capacity_aware=True): skip hospitals at/over the overload threshold when an
        alternative with spare capacity exists.
        """
        assignments: list[AssignmentResult] = []
        pending = state.get_pending_requests()
        available = list(state.get_available_ambulances())

        for request in pending:
            if not available:
                assignments.append(
                    AssignmentResult(
                        ambulance_id="",
                        request_id=request.request_id,
                        is_feasible=False,
                        reason="No available ambulance remains.",
                    )
                )
                continue

            best: AssignmentResult | None = None
            for ambulance in available:
                to_scene = routing_service.shortest_path(
                    state.city_graph, ambulance.nearest_node_id, request.nearest_node_id
                )
                if not to_scene.is_feasible:
                    continue

                hospital_ids = []
                excluded: set[str] = set()
                for hospital in state.hospitals.values():
                    if hospital.available_beds <= 0:
                        excluded.add(hospital.nearest_node_id)
                        continue
                    if capacity_aware and hospital.compute_load() >= overload_threshold:
                        # Prefer not to send here unless no alternative exists.
                        continue
                    hospital_ids.append(hospital.nearest_node_id)

                hid_node, to_hospital = routing_service.nearest_reachable(
                    state.city_graph, request.nearest_node_id, hospital_ids
                )
                if hid_node is None:
                    # Fallback: any hospital with a bed, including overloaded.
                    fallback_nodes = [
                        h.nearest_node_id
                        for h in state.hospitals.values()
                        if h.available_beds > 0
                    ]
                    hid_node, to_hospital = routing_service.nearest_reachable(
                        state.city_graph, request.nearest_node_id, fallback_nodes
                    )
                if hid_node is None or not to_hospital.is_feasible:
                    continue

                hospital = next(h for h in state.hospitals.values() if h.nearest_node_id == hid_node)
                total_time = to_scene.total_time_s + to_hospital.total_time_s
                combined = AssignmentResult(
                    ambulance_id=ambulance.ambulance_id,
                    request_id=request.request_id,
                    hospital_id=hospital.hospital_id,
                    route=to_hospital,
                    estimated_arrival_s=total_time,
                    is_feasible=True,
                    reason="OK",
                )
                # stash scene time on route metadata via estimated_arrival
                if best is None or (combined.estimated_arrival_s or 0) < (best.estimated_arrival_s or 0):
                    best = combined

            if best is None or not best.is_feasible:
                assignments.append(
                    AssignmentResult(
                        ambulance_id="",
                        request_id=request.request_id,
                        is_feasible=False,
                        reason="No passable ambulance-to-hospital path with remaining capacity.",
                    )
                )
                continue

            ambulance = state.ambulances[best.ambulance_id]
            hospital = state.hospitals[best.hospital_id]  # type: ignore[index]
            ambulance.assign(request.request_id)
            hospital.admit_patient()
            available = [a for a in available if a.ambulance_id != ambulance.ambulance_id]
            assignments.append(best)

        return assignments

    def snapshot(
        self,
        state: SimulationState,
        started_at: datetime,
        assignments: list[AssignmentResult],
        extra_events: list[CascadeEvent],
    ) -> CascadeStep:
        settings = get_settings()
        probe = [a.nearest_node_id for a in state.ambulances.values()]
        probe.extend(r.nearest_node_id for r in state.requests.values())
        isolated = self.isolate_facilities(state.city_graph, state.hospitals, probe)
        unreachable = [a.request_id for a in assignments if not a.is_feasible]
        events = list(extra_events)
        for assignment in assignments:
            if assignment.is_feasible:
                events.append(
                    CascadeEvent(
                        step=state.step,
                        event_type="ASSIGNMENT",
                        description=(
                            f"Ambulance {assignment.ambulance_id} assigned to {assignment.request_id} "
                            f"→ {assignment.hospital_id} in {assignment.estimated_arrival_s:.0f}s "
                            "(simulated travel time, not an observed ETA)."
                        ),
                        affected_entity_id=assignment.request_id,
                        severity=0.2,
                    )
                )
            else:
                events.append(
                    CascadeEvent(
                        step=state.step,
                        event_type="REQUEST_UNREACHABLE",
                        description=assignment.reason,
                        affected_entity_id=assignment.request_id,
                        severity=0.9,
                    )
                )
        for hid in isolated:
            events.append(
                CascadeEvent(
                    step=state.step,
                    event_type="FACILITY_ISOLATED",
                    description=f"Hospital {hid} has no passable path from current resources/requests.",
                    affected_entity_id=hid,
                    severity=0.85,
                )
            )
        for hospital in state.hospitals.values():
            load = hospital.compute_load()
            if hospital.is_overloaded(settings.hospital_overload_threshold):
                events.append(
                    CascadeEvent(
                        step=state.step,
                        event_type="HOSPITAL_OVERLOADED",
                        description=f"Hospital {hospital.hospital_id} occupancy {load:.0%} (simulated load).",
                        affected_entity_id=hospital.hospital_id,
                        severity=min(1.0, load),
                    )
                )

        active = [eid for eid, edge in state.city_graph.edges.items() if edge.status in ("DEGRADED", "CLOSED")]
        return CascadeStep(
            step_index=state.step,
            timestamp=compute_simulation_timestamp(started_at, state.step, settings.simulation_step_minutes),
            active_disruptions=active,
            unreachable_requests=unreachable,
            isolated_facilities=isolated,
            hospital_loads={hid: h.compute_load() for hid, h in state.hospitals.items()},
            cascade_events=events,
        )


cascade_service = CascadeService()
