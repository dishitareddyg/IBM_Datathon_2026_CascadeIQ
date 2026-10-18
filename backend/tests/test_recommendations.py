"""
tests/test_recommendations.py
------------------------------
Tests for the intervention recommendations endpoint.
"""

from __future__ import annotations

import pytest


async def _run_sim_and_get_id(async_client, sample_scenario) -> str:
    r = await async_client.post("/api/v1/simulations/run", json=sample_scenario)
    assert r.status_code == 201
    return r.json()["data"]["simulation_id"]


@pytest.mark.asyncio
async def test_recommendations_200(async_client, sample_scenario):
    sim_id = await _run_sim_and_get_id(async_client, sample_scenario)
    resp = await async_client.post(
        "/api/v1/recommendations",
        json={"simulation_id": sim_id, "objective_lambda": 0.3, "objective_mu": 0.1, "max_recommendations": 5},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_recommendations_result_structure(async_client, sample_scenario):
    sim_id = await _run_sim_and_get_id(async_client, sample_scenario)
    resp = await async_client.post(
        "/api/v1/recommendations",
        json={"simulation_id": sim_id, "objective_lambda": 0.3, "objective_mu": 0.1, "max_recommendations": 5},
    )
    data = resp.json()["data"]
    assert "simulation_id" in data
    assert "ranked_interventions" in data
    assert "objective_scores" in data
    assert "computation_latency_ms" in data
    assert "method_note" in data
    assert data["computation_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_recommendations_not_found(async_client):
    resp = await async_client.post(
        "/api/v1/recommendations",
        json={"simulation_id": "nonexistent-sim-id", "objective_lambda": 0.3, "objective_mu": 0.1, "max_recommendations": 5},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_recommendations_method_note_present(async_client, sample_scenario):
    sim_id = await _run_sim_and_get_id(async_client, sample_scenario)
    resp = await async_client.post(
        "/api/v1/recommendations",
        json={"simulation_id": sim_id, "objective_lambda": 0.3, "objective_mu": 0.1, "max_recommendations": 3},
    )
    data = resp.json()["data"]
    assert "heuristic" in data["method_note"].lower() or "greedy" in data["method_note"].lower()


@pytest.mark.asyncio
async def test_recommendations_max_count_respected(async_client, sample_scenario):
    sim_id = await _run_sim_and_get_id(async_client, sample_scenario)
    max_recs = 2
    resp = await async_client.post(
        "/api/v1/recommendations",
        json={"simulation_id": sim_id, "objective_lambda": 0.3, "objective_mu": 0.1, "max_recommendations": max_recs},
    )
    data = resp.json()["data"]
    assert len(data["ranked_interventions"]) <= max_recs
