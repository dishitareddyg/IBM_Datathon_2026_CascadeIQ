"""Deterministic step-based simulation orchestrator."""

from __future__ import annotations

import random
from copy import deepcopy
from uuid import uuid4

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.models.entities import SimulationResult as DomainSimulationResult
from app.models.scenario import (
    Ambulance,
    EmergencyRequest,
    Hospital,
    RoadDisruption,
    SimulationState,
)
from app.schemas.scenario import ScenarioInput
from app.schemas.simulation import (
    AmbulanceAssignment,
    CascadeEventSchema,
    CascadeStep as CascadeStepSchema,
    RouteSegment,
    SimulationResult,
)
from app.services.cascade_service import cascade_service
from app.services.graph_service import graph_service
from app.services.intervention_service import intervention_service
from app.services.risk_service import WeatherSignals, risk_service
from app.services.routing_service import routing_service
from app.utils.time import now_utc
from app.repositories.scenario_repository import scenario_repo

_WARNING_SCORE = {
    "WATCH": 0.25,
    "WARNING": 0.5,
    "SEVERE": 0.75,
    "EXTREME": 1.0,
}


def _weather_signals(scenario: ScenarioInput, rng: random.Random) -> WeatherSignals:
    """
    Build explicit weather inputs. Synthetic values are tagged as synthetic.
    Live/historical modes still fall back to synthetic in Phase 1 when IMD is absent.
    """
    # Deterministic synthetic rainfall from seed — not an observation.
    base = {"synthetic": 70.0, "historical": 55.0, "live": 40.0}[scenario.weather_mode]
    rain_24h = max(0.0, rng.gauss(base, 8.0))
    rain_1h = max(0.0, rain_24h / 12.0)
    warn = 0.5 if rain_24h >= 50 else 0.2
    kind = "synthetic" if scenario.weather_mode == "synthetic" else scenario.weather_mode
    if scenario.weather_mode == "live":
        from app.core.config import get_settings as _gs
        if not _gs().imd_configured:
            kind = "synthetic"
    return WeatherSignals(
        rainfall_mm_1h=round(rain_1h, 2),
        rainfall_mm_24h=round(rain_24h, 2),
        warning_severity_score=warn,
        rainfall_kind=kind,
        warning_kind=kind if warn > 0 else "none",
    )


def _build_state(scenario: ScenarioInput, seed: int) -> SimulationState:
    graph = graph_service.get_copy()
    settings = get_settings()
    if len(scenario.hospitals) > settings.max_hospitals:
        raise ValidationError("Too many hospitals.", field="hospitals")
    if len(scenario.ambulances) > settings.max_ambulances:
        raise ValidationError("Too many ambulances.", field="ambulances")
    if len(scenario.emergency_requests) > settings.max_requests:
        raise ValidationError("Too many emergency requests.", field="emergency_requests")
    if scenario.simulation_steps > settings.max_scenario_steps:
        raise ValidationError("simulation_steps exceeds configured maximum.", field="simulation_steps")

    hospitals: dict[str, Hospital] = {}
    for item in scenario.hospitals:
        node = routing_service.snap(graph, item.lat, item.lon)
        if node is None:
            raise ValidationError(f"Hospital {item.hospital_id} could not be snapped to the graph.")
        hospital = Hospital(
            hospital_id=item.hospital_id,
            name=item.name,
            lat=item.lat,
            lon=item.lon,
            nearest_node_id=node,
            total_beds=item.total_beds,
            available_beds=item.available_beds,
            icu_beds=item.icu_beds,
        )
        hospital.compute_load()
        hospitals[item.hospital_id] = hospital

    ambulances: dict[str, Ambulance] = {}
    for item in scenario.ambulances:
        node = routing_service.snap(graph, item.lat, item.lon)
        if node is None:
            raise ValidationError(f"Ambulance {item.ambulance_id} could not be snapped to the graph.")
        ambulances[item.ambulance_id] = Ambulance(
            ambulance_id=item.ambulance_id,
            lat=item.lat,
            lon=item.lon,
            nearest_node_id=node,
            is_available=item.is_available,
            assigned_request_id=item.assigned_request_id,
        )

    requests: dict[str, EmergencyRequest] = {}
    for item in scenario.emergency_requests:
        node = routing_service.snap(graph, item.origin_lat, item.origin_lon)
        if node is None:
            raise ValidationError(f"Request {item.request_id} could not be snapped to the graph.")
        requests[item.request_id] = EmergencyRequest(
            request_id=item.request_id,
            origin_lat=item.origin_lat,
            origin_lon=item.origin_lon,
            nearest_node_id=node,
            priority=item.priority,
            created_at=item.created_at,
        )

    disruptions = {
        d.edge_id: RoadDisruption(
            edge_id=d.edge_id,
            status=d.status.value if hasattr(d.status, "value") else str(d.status),
            severity=d.severity,
            confidence=d.confidence,
            cause=d.cause,
            estimated_by=d.estimated_by,
        )
        for d in scenario.road_disruptions
    }
    return SimulationState(
        scenario_id=scenario.scenario_id,
        seed=seed,
        hospitals=hospitals,
        ambulances=ambulances,
        requests=requests,
        disruptions=disruptions,
        city_graph=graph,
    )


def _to_schema(
    simulation_id: str,
    scenario: ScenarioInput,
    started_at,
    finished_at,
    steps,
    assignments,
    status: str = "COMPLETED",
) -> SimulationResult:
    schema_steps: list[CascadeStepSchema] = []
    for step in steps:
        schema_steps.append(
            CascadeStepSchema(
                step_index=step.step_index,
                timestamp=step.timestamp,
                active_disruptions=step.active_disruptions,
                unreachable_requests=step.unreachable_requests,
                isolated_facilities=step.isolated_facilities,
                hospital_loads={k: round(v, 4) for k, v in step.hospital_loads.items()},
                cascade_events=[
                    CascadeEventSchema(
                        step_index=ev.step,
                        event_type=ev.event_type,
                        description=ev.description,
                        affected_entity_id=ev.affected_entity_id,
                        severity=ev.severity,
                        provenance="simulated",
                    )
                    for ev in step.cascade_events
                ],
            )
        )
    final_assignments = [
        AmbulanceAssignment(
            ambulance_id=a.ambulance_id,
            request_id=a.request_id,
            hospital_id=a.hospital_id,
            route=RouteSegment(
                edge_ids=a.route.edge_ids if a.route else [],
                total_distance_m=a.route.total_distance_m if a.route else 0.0,
                total_time_s=a.route.total_time_s if a.route else 0.0,
                is_feasible=a.route.is_feasible if a.route else False,
            ),
            estimated_arrival_s=a.estimated_arrival_s or 0.0,
        )
        for a in assignments
        if a.is_feasible
    ]
    return SimulationResult(
        simulation_id=simulation_id,
        scenario_id=scenario.scenario_id,
        seed=scenario.seed,
        status=status,
        steps=schema_steps,
        final_assignments=final_assignments,
        created_at=started_at,
        completed_at=finished_at,
    )


class SimulationService:
    def run(
        self,
        scenario: ScenarioInput,
        *,
        policy: str = "cascadeiq",
        persist: bool = True,
    ) -> tuple[SimulationResult, SimulationState, list]:
        """
        policy:
          baseline  — explicit scenario disruptions only; nearest reachable hospital with a bed.
          cascadeiq — inferred flood DEGRADATION + capacity-aware assignment.
        """
        rng = random.Random(scenario.seed)
        started = now_utc()
        state = _build_state(scenario, scenario.seed)
        signals = _weather_signals(scenario, rng)

        from app.models.entities import CascadeEvent

        extra_events: list[CascadeEvent] = []
        if policy == "cascadeiq":
            degraded = risk_service.apply_inferred_risk(state.city_graph, signals)
            extra_events.extend(
                CascadeEvent(
                    step=0,
                    event_type="ROAD_DEGRADED",
                    description=(
                        f"Edge {edge_id} marked DEGRADED from inferred flood-related risk using "
                        f"{signals.rainfall_kind} rainfall {signals.rainfall_mm_24h:.1f} mm/24h. "
                        "A weather alert is not treated as observed inundation."
                    ),
                    affected_entity_id=edge_id,
                    severity=0.6,
                )
                for edge_id in degraded
            )

        applied = risk_service.apply_scenario_disruptions(
            state.city_graph, list(state.disruptions.values())
        )

        for edge_id in applied:
            extra_events.append(
                CascadeEvent(
                    step=0,
                    event_type="ROAD_CLOSED" if state.city_graph.edges[edge_id].status == "CLOSED" else "ROAD_DEGRADED",
                    description=(
                        f"Scenario disruption applied to {edge_id} "
                        f"({state.city_graph.edges[edge_id].status}, provenance=scenario)."
                    ),
                    affected_entity_id=edge_id,
                    severity=state.disruptions[edge_id].severity,
                )
            )

        settings = get_settings()
        capacity_aware = policy == "cascadeiq"
        all_assignments = []
        schema_ready_steps = []

        for step_idx in range(scenario.simulation_steps):
            state.step = step_idx
            # Ambulances remain busy after assignment; later steps record residual unserved demand.
            step_assignments = cascade_service.assign_requests(
                state,
                capacity_aware=capacity_aware,
                overload_threshold=settings.hospital_overload_threshold,
            )
            if step_idx == 0:
                all_assignments = step_assignments
            snapshot = cascade_service.snapshot(
                state,
                started,
                all_assignments,
                extra_events if step_idx == 0 else [],
            )
            schema_ready_steps.append(snapshot)

        finished = now_utc()
        simulation_id = str(uuid4())
        result = _to_schema(
            simulation_id, scenario, started, finished, schema_ready_steps, all_assignments
        )
        result_with_meta = result.model_copy(
            update={
                "disclaimer": (
                    "Results are computer-generated estimates for research and education. "
                    "They are not observations, not validated real-world predictions, and must not "
                    "be used for operational emergency dispatch."
                )
            }
        )
        if persist:
            scenario_repo.save_sync(result_with_meta)
            scenario_repo.save_runtime(simulation_id, state, all_assignments, scenario)
        return result_with_meta, state, all_assignments


simulation_service = SimulationService()
