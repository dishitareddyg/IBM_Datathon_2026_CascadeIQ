"""
tests/test_simulation.py
------------------------
Tests for the simulation engine endpoints and core routing invariants.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _run_sim(async_client, scenario: dict) -> dict:
    """POST a scenario and return the JSON response body."""
    r = await async_client.post("/api/v1/simulations", json=scenario)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Basic simulation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulation_returns_result(async_client, sample_scenario):
    data = await _run_sim(async_client, sample_scenario)
    assert "data" in data
    result = data["data"]
    assert "simulation_id" in result
    assert result["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_simulation_has_steps(async_client, sample_scenario):
    data = await _run_sim(async_client, sample_scenario)
    steps = data["data"]["steps"]
    assert isinstance(steps, list)
    assert len(steps) == sample_scenario["simulation_steps"]


@pytest.mark.asyncio
async def test_simulation_has_disclaimer(async_client, sample_scenario):
    data = await _run_sim(async_client, sample_scenario)
    result = data["data"]
    assert "disclaimer" in result
    assert len(result["disclaimer"]) > 10


@pytest.mark.asyncio
async def test_simulation_cascade_step_structure(async_client, sample_scenario):
    data = await _run_sim(async_client, sample_scenario)
    step = data["data"]["steps"][0]
    assert "step_index" in step
    assert "timestamp" in step
    assert "unreachable_requests" in step
    assert "isolated_facilities" in step
    assert "hospital_loads" in step
    assert "cascade_events" in step
    assert isinstance(step["unreachable_requests"], list)
    assert isinstance(step["isolated_facilities"], list)
    assert isinstance(step["hospital_loads"], dict)


@pytest.mark.asyncio
async def test_simulation_hospital_loads_in_range(async_client, sample_scenario):
    """Hospital load values must be non-negative floats."""
    data = await _run_sim(async_client, sample_scenario)
    for step in data["data"]["steps"]:
        for hid, load in step["hospital_loads"].items():
            assert isinstance(load, (int, float))
            assert load >= 0.0, f"Negative load for {hid}: {load}"


# ---------------------------------------------------------------------------
# Deterministic seed test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deterministic_seed(async_client, sample_scenario):
    """Same seed must produce identical cascade timelines."""
    r1 = await _run_sim(async_client, sample_scenario)
    r2 = await _run_sim(async_client, sample_scenario)

    steps1 = r1["data"]["steps"]
    steps2 = r2["data"]["steps"]

    assert len(steps1) == len(steps2)
    for s1, s2 in zip(steps1, steps2):
        assert s1["hospital_loads"] == s2["hospital_loads"]
        assert sorted(s1["unreachable_requests"]) == sorted(s2["unreachable_requests"])
        assert sorted(s1["isolated_facilities"]) == sorted(s2["isolated_facilities"])


# ---------------------------------------------------------------------------
# Retrieve simulation by ID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_simulation_by_id(async_client, sample_scenario):
    post_data = await _run_sim(async_client, sample_scenario)
    sim_id = post_data["data"]["simulation_id"]

    get_resp = await async_client.get(f"/api/v1/simulations/{sim_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()["data"]
    assert get_data["simulation_id"] == sim_id


@pytest.mark.asyncio
async def test_get_simulation_not_found(async_client):
    resp = await async_client.get("/api/v1/simulations/nonexistent-id-xyz-12345")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Closed-road routing invariant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_closed_road_disruption_recorded(async_client, sample_scenario_with_disruptions):
    """A CLOSED disruption must appear in active_disruptions of cascade steps."""
    data = await _run_sim(async_client, sample_scenario_with_disruptions)
    steps = data["data"]["steps"]
    all_disruptions = [d for step in steps for d in step["active_disruptions"]]
    # At minimum, the scenario disruption edge must be tracked
    assert len(all_disruptions) >= 1


# ---------------------------------------------------------------------------
# Bundled graph routing unit test (no HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bundled_graph_nodes_exist():
    """Bundled graph must have nodes and edges after build."""
    from app.services.graph_service import build_bundled_graph
    graph = build_bundled_graph()
    assert graph.node_count() >= 10
    assert graph.edge_count() >= 15


@pytest.mark.asyncio
async def test_bundled_graph_passable_subgraph():
    """get_passable_graph() must exclude CLOSED edges."""
    from app.services.graph_service import build_bundled_graph
    graph = build_bundled_graph()
    # Manually close one edge
    edges = list(graph.edges.values())
    if not edges:
        pytest.skip("No edges in bundled graph")
    edge = edges[0]
    edge.status = "CLOSED"
    passable = graph.get_passable_graph()
    # The closed edge should NOT appear in passable graph
    has_closed = passable.has_edge(edge.source, edge.target)
    # Reset
    edge.status = "OPEN"
    # If only one direction exists, it should be excluded
    assert not has_closed, "CLOSED edge appeared in passable subgraph"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_scenario_returns_422(async_client):
    """Missing required fields must return HTTP 422."""
    resp = await async_client.post("/api/v1/simulations", json={"invalid": "data"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_simulations(async_client, sample_scenario):
    """GET /api/v1/simulations/ must return a list of IDs."""
    await _run_sim(async_client, sample_scenario)
    resp = await async_client.get("/api/v1/simulations/")
    assert resp.status_code == 200
    ids = resp.json()["data"]
    assert isinstance(ids, list)
    assert len(ids) >= 1
