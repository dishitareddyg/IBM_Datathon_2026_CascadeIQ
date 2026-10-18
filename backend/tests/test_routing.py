"""Routing invariants: closed roads, isolation, capacity, seeds."""

from __future__ import annotations

import pytest

from app.schemas.scenario import ScenarioInput
from app.services.graph_service import build_bundled_graph, graph_service
from app.services.risk_service import risk_service
from app.services.routing_service import routing_service
from app.services.simulation_service import simulation_service
from app.models.scenario import RoadDisruption


def test_closed_edges_are_not_traversed():
    graph = build_bundled_graph()
    open_route = routing_service.shortest_path(graph, "majestic", "koramangala")
    assert open_route.is_feasible

    # Close every edge on that path.
    for edge_id in open_route.edge_ids:
        edge = graph.edges[edge_id]
        edge.status = "CLOSED"
        if graph.nx_graph.has_edge(edge.source, edge.target):
            graph.nx_graph[edge.source][edge.target]["status"] = "CLOSED"

    closed_route = routing_service.shortest_path(graph, "majestic", "koramangala")
    if closed_route.is_feasible:
        assert set(open_route.edge_ids).isdisjoint(closed_route.edge_ids)
    # Direct edge must not be used if it was closed.
    for u, v in zip(open_route.path_nodes, open_route.path_nodes[1:]):
        if graph.edges.get(f"{u}_{v}") and graph.edges[f"{u}_{v}"].status == "CLOSED":
            assert f"{u}_{v}" not in closed_route.edge_ids


def test_fully_cut_hospital_is_unreachable():
    graph = build_bundled_graph()
    hospital_node = "victoria_hosp"
    for edge in list(graph.edges.values()):
        if edge.target == hospital_node or edge.source == hospital_node:
            edge.status = "CLOSED"

    result = routing_service.shortest_path(graph, "indiranagar", hospital_node)
    assert result.is_feasible is False
    assert result.infeasibility_reason


def test_passable_graph_excludes_closed():
    graph = build_bundled_graph()
    edge = next(iter(graph.edges.values()))
    edge.status = "CLOSED"
    passable = graph.get_passable_graph()
    assert not passable.has_edge(edge.source, edge.target)


def test_scenario_closed_disruption_applied():
    graph = graph_service.get_copy()
    edge_id = next(iter(graph.edges))
    risk_service.apply_scenario_disruptions(
        graph,
        [
            RoadDisruption(
                edge_id=edge_id,
                status="CLOSED",
                severity=1.0,
                confidence=0.9,
                cause="test",
                estimated_by="test",
            )
        ],
    )
    assert graph.edges[edge_id].status == "CLOSED"
    src, tgt = graph.edges[edge_id].source, graph.edges[edge_id].target
    route = routing_service.shortest_path(graph, src, tgt)
    assert route.is_feasible is False or edge_id not in route.edge_ids


def test_capacity_blocks_further_admissions(sample_scenario):
    payload = dict(sample_scenario)
    payload["hospitals"] = [
        {
            "hospital_id": "H1",
            "name": "Tiny Hospital",
            "lat": 12.9612,
            "lon": 77.5726,
            "total_beds": 2,
            "available_beds": 1,
            "icu_beds": 0,
        }
    ]
    payload["emergency_requests"] = [
        {"request_id": "R1", "origin_lat": 12.95, "origin_lon": 77.59, "priority": "CRITICAL"},
        {"request_id": "R2", "origin_lat": 12.98, "origin_lon": 77.60, "priority": "HIGH"},
        {"request_id": "R3", "origin_lat": 12.93, "origin_lon": 77.62, "priority": "MEDIUM"},
    ]
    payload["ambulances"] = [
        {"ambulance_id": "A1", "lat": 12.9767, "lon": 77.5713, "is_available": True},
        {"ambulance_id": "A2", "lat": 12.9279, "lon": 77.6271, "is_available": True},
        {"ambulance_id": "A3", "lat": 12.9641, "lon": 77.5984, "is_available": True},
    ]
    scenario = ScenarioInput(**payload)
    result, state, assignments = simulation_service.run(scenario, policy="baseline", persist=False)
    admitted = [a for a in assignments if a.is_feasible]
    assert len(admitted) <= 1
    assert state.hospitals["H1"].available_beds == 0
    unreachable = [a for a in assignments if not a.is_feasible]
    assert len(unreachable) >= 1


def test_deterministic_simulation_seed(sample_scenario):
    scenario = ScenarioInput(**sample_scenario)
    r1, _, _ = simulation_service.run(scenario, policy="cascadeiq", persist=False)
    r2, _, _ = simulation_service.run(scenario, policy="cascadeiq", persist=False)
    assert [s.hospital_loads for s in r1.steps] == [s.hospital_loads for s in r2.steps]
    assert [s.unreachable_requests for s in r1.steps] == [s.unreachable_requests for s in r2.steps]


def test_weather_never_closes_roads_alone():
    graph = build_bundled_graph()
    from app.services.risk_service import WeatherSignals

    risk_service.apply_inferred_risk(
        graph,
        WeatherSignals(
            rainfall_mm_1h=80,
            rainfall_mm_24h=200,
            warning_severity_score=1.0,
            rainfall_kind="synthetic",
            warning_kind="synthetic",
        ),
    )
    assert all(edge.status != "CLOSED" for edge in graph.edges.values())
