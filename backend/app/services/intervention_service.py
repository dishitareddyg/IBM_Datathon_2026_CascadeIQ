"""
Constrained search over a small set of intervention types.

Supported actions:
  * REROUTE an ambulance to a different passable path (already implied by
    recomputing Dijkstra after disruptions — here we try pairing a different
    remaining ambulance with an unreachable request).
  * DIVERT a request to a different reachable hospital.
  * PREPOSITION a limited idle resource toward an isolated facility.

Objective (lower is better):
  score = response_time_s + lambda * hospital_overload + mu * intervention_cost

This is exhaustive search over a bounded candidate set. It does not guarantee
global optimality.
"""

from __future__ import annotations

import time
from uuid import uuid4

from app.models.entities import InterventionCandidate, RouteResult
from app.models.scenario import SimulationState
from app.schemas.recommendation import (
    InterventionAction,
    InterventionType,
    RecommendationResult,
)
from app.schemas.simulation import RouteSegment
from app.services.routing_service import routing_service


def _route_segment(route: RouteResult | None) -> RouteSegment | None:
    if route is None:
        return None
    return RouteSegment(
        edge_ids=route.edge_ids,
        total_distance_m=route.total_distance_m,
        total_time_s=route.total_time_s,
        is_feasible=route.is_feasible,
    )


def _score(response_time_s: float, overload: float, cost: float, lam: float, mu: float) -> float:
    return response_time_s + lam * overload + mu * cost


class InterventionService:
    def recommend(
        self,
        state: SimulationState,
        assignments: list,
        *,
        objective_lambda: float,
        objective_mu: float,
        max_recommendations: int,
    ) -> RecommendationResult:
        started = time.perf_counter()
        candidates: list[InterventionCandidate] = []

        feasible_assignments = [a for a in assignments if a.is_feasible]
        unreachable = [a for a in assignments if not a.is_feasible]
        mean_rt = (
            sum(a.estimated_arrival_s or 0.0 for a in feasible_assignments) / len(feasible_assignments)
            if feasible_assignments
            else 0.0
        )
        mean_overload = (
            sum(h.compute_load() for h in state.hospitals.values()) / max(len(state.hospitals), 1)
        )

        idle = [a for a in state.ambulances.values() if a.is_available]
        busy = [a for a in state.ambulances.values() if not a.is_available]

        # --- REROUTE: try idle (or any) ambulance to unreachable request, then hospital ---
        for failed in unreachable:
            request = state.requests.get(failed.request_id)
            if request is None:
                continue
            pool = idle or list(state.ambulances.values())
            found = False
            for ambulance in pool:
                to_scene = routing_service.shortest_path(
                    state.city_graph, ambulance.nearest_node_id, request.nearest_node_id
                )
                if not to_scene.is_feasible:
                    continue
                hosp_nodes = [h.nearest_node_id for h in state.hospitals.values() if h.available_beds > 0]
                hid, to_h = routing_service.nearest_reachable(
                    state.city_graph, request.nearest_node_id, hosp_nodes
                )
                if hid is None:
                    continue
                hospital = next(h for h in state.hospitals.values() if h.nearest_node_id == hid)
                rt = to_scene.total_time_s + to_h.total_time_s
                cost = 1.0
                overload = hospital.compute_load()
                score = _score(rt, overload, cost, objective_lambda, objective_mu)
                candidates.append(
                    InterventionCandidate(
                        action_id=f"reroute_{uuid4().hex[:8]}",
                        intervention_type="REROUTE",
                        description=(
                            f"Reroute ambulance {ambulance.ambulance_id} to request {request.request_id} "
                            f"then hospital {hospital.hospital_id} on a currently passable path."
                        ),
                        target_ambulance_id=ambulance.ambulance_id,
                        target_request_id=request.request_id,
                        target_hospital_id=hospital.hospital_id,
                        new_route=to_h,
                        feasible=True,
                        objective_score=score,
                        response_time_improvement_s=max(0.0, mean_rt - rt) if mean_rt else 0.0,
                        hospital_overload_reduction=max(0.0, mean_overload - overload),
                        intervention_cost=cost,
                    )
                )
                found = True
                break
            if not found:
                candidates.append(
                    InterventionCandidate(
                        action_id=f"reroute_reject_{uuid4().hex[:8]}",
                        intervention_type="REROUTE",
                        description=f"Reroute for request {failed.request_id} is infeasible.",
                        target_request_id=failed.request_id,
                        feasible=False,
                        infeasibility_reason=failed.reason or "No passable ambulance-hospital pair.",
                        objective_score=float("inf"),
                        intervention_cost=1.0,
                    )
                )

        # --- DIVERT: move an assigned request from an overloaded hospital to a spare one ---
        overloaded = [h for h in state.hospitals.values() if h.is_overloaded()]
        spare = [h for h in state.hospitals.values() if h.available_beds > 0 and not h.is_overloaded()]
        for assignment in feasible_assignments:
            current = state.hospitals.get(assignment.hospital_id or "")
            request = state.requests.get(assignment.request_id)
            if current is None or request is None or current not in overloaded:
                continue
            if not spare:
                candidates.append(
                    InterventionCandidate(
                        action_id=f"divert_reject_{uuid4().hex[:8]}",
                        intervention_type="DIVERT",
                        description=f"Cannot divert {assignment.request_id}: no hospital with spare capacity.",
                        target_request_id=assignment.request_id,
                        target_hospital_id=current.hospital_id,
                        feasible=False,
                        infeasibility_reason="All other hospitals lack remaining beds or are overloaded.",
                        intervention_cost=0.5,
                    )
                )
                continue
            hid, route = routing_service.nearest_reachable(
                state.city_graph,
                request.nearest_node_id,
                [h.nearest_node_id for h in spare],
            )
            if hid is None:
                candidates.append(
                    InterventionCandidate(
                        action_id=f"divert_reject_{uuid4().hex[:8]}",
                        intervention_type="DIVERT",
                        description=f"Divert of {assignment.request_id} has no passable path to a spare hospital.",
                        target_request_id=assignment.request_id,
                        feasible=False,
                        infeasibility_reason="Spare-capacity hospitals are not reachable on OPEN/DEGRADED roads.",
                        intervention_cost=0.5,
                    )
                )
                continue
            dest = next(h for h in spare if h.nearest_node_id == hid)
            rt = route.total_time_s
            score = _score(rt, dest.compute_load(), 0.5, objective_lambda, objective_mu)
            candidates.append(
                InterventionCandidate(
                    action_id=f"divert_{uuid4().hex[:8]}",
                    intervention_type="DIVERT",
                    description=(
                        f"Divert request {assignment.request_id} from overloaded "
                        f"{current.hospital_id} to {dest.hospital_id}."
                    ),
                    target_request_id=assignment.request_id,
                    target_hospital_id=dest.hospital_id,
                    new_route=route,
                    feasible=True,
                    objective_score=score,
                    response_time_improvement_s=max(0.0, (assignment.estimated_arrival_s or rt) - rt),
                    hospital_overload_reduction=max(0.0, current.compute_load() - dest.compute_load()),
                    intervention_cost=0.5,
                )
            )

        # --- PREPOSITION: move one idle ambulance toward an isolated hospital ---
        isolated_ids = [
            h.hospital_id for h in state.hospitals.values() if not h.is_accessible
        ]
        if isolated_ids and not idle:
            candidates.append(
                InterventionCandidate(
                    action_id=f"prepos_reject_{uuid4().hex[:8]}",
                    intervention_type="PREPOSITION",
                    description="Pre-positioning rejected: no idle ambulance remains.",
                    target_hospital_id=isolated_ids[0],
                    feasible=False,
                    infeasibility_reason="Resource availability constraint: all ambulances are assigned.",
                    intervention_cost=0.3,
                )
            )
        for hid in isolated_ids:
            hospital = state.hospitals[hid]
            if not idle:
                break
            ambulance = idle[0]
            route = routing_service.shortest_path(
                state.city_graph, ambulance.nearest_node_id, hospital.nearest_node_id
            )
            if not route.is_feasible:
                candidates.append(
                    InterventionCandidate(
                        action_id=f"prepos_reject_{uuid4().hex[:8]}",
                        intervention_type="PREPOSITION",
                        description=f"Cannot pre-position near {hid}: facility is currently unreachable.",
                        target_ambulance_id=ambulance.ambulance_id,
                        target_hospital_id=hid,
                        feasible=False,
                        infeasibility_reason="No passable path from the idle unit to the isolated facility.",
                        intervention_cost=0.3,
                    )
                )
                continue
            score = _score(route.total_time_s, hospital.compute_load(), 0.3, objective_lambda, objective_mu)
            candidates.append(
                InterventionCandidate(
                    action_id=f"prepos_{uuid4().hex[:8]}",
                    intervention_type="PREPOSITION",
                    description=(
                        f"Pre-position idle ambulance {ambulance.ambulance_id} toward facility {hid} "
                        "before further closures isolate staging options."
                    ),
                    target_ambulance_id=ambulance.ambulance_id,
                    target_hospital_id=hid,
                    new_route=route,
                    feasible=True,
                    objective_score=score,
                    intervention_cost=0.3,
                )
            )
            idle = idle[1:]  # limited resource: at most one move per idle unit

        feasible = [c for c in candidates if c.feasible]
        infeasible = [c for c in candidates if not c.feasible]
        feasible.sort(key=lambda c: c.objective_score)
        ranked = (feasible + infeasible)[:max_recommendations]

        actions: list[InterventionAction] = []
        scores: dict[str, float] = {}
        for c in ranked:
            itype = InterventionType(c.intervention_type)
            score_val = None if not c.feasible or c.objective_score == float("inf") else round(c.objective_score, 4)
            actions.append(
                InterventionAction(
                    action_id=c.action_id,
                    type=itype,
                    description=c.description,
                    target_ambulance_id=c.target_ambulance_id,
                    target_request_id=c.target_request_id,
                    target_hospital_id=c.target_hospital_id,
                    new_route=_route_segment(c.new_route),
                    feasible=c.feasible,
                    infeasibility_reason=c.infeasibility_reason,
                    objective_score=score_val,
                    response_time_s=c.new_route.total_time_s if c.new_route else None,
                    hospital_overload=None,
                    intervention_cost=c.intervention_cost,
                )
            )
            if score_val is not None:
                scores[c.action_id] = score_val

        latency_ms = (time.perf_counter() - started) * 1000
        return RecommendationResult(
            simulation_id="",
            ranked_interventions=actions,
            objective_scores=scores,
            computation_latency_ms=round(latency_ms, 2),
            method_note=(
                "Bounded heuristic search over REROUTE, DIVERT and PREPOSITION candidates. "
                "Objective = response_time_s + λ×hospital_overload + μ×intervention_cost. "
                "Global optimality is not guaranteed."
            ),
        )


intervention_service = InterventionService()
