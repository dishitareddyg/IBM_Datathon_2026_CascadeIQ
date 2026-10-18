"""
tests/test_evaluation.py
------------------------
Tests for the baseline vs CascadeIQ evaluation endpoint.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_evaluation_returns_200(async_client, sample_scenario):
    body = {
        "scenario_input": sample_scenario,
        "objective_lambda": 0.3,
        "objective_mu": 0.1,
    }
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_evaluation_has_both_policies(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    data = resp.json()["data"]
    assert "baseline" in data
    assert "cascadeiq" in data


@pytest.mark.asyncio
async def test_evaluation_policy_names(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    data = resp.json()["data"]
    assert data["baseline"]["policy_name"] == "baseline"
    assert data["cascadeiq"]["policy_name"] == "cascadeiq"


@pytest.mark.asyncio
async def test_evaluation_metrics_present(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    data = resp.json()["data"]
    for policy_key in ("baseline", "cascadeiq"):
        metrics = {m["name"]: m for m in data[policy_key]["metrics"]}
        assert "mean_response_time_s" in metrics, f"Missing metric in {policy_key}"
        assert "unreachable_count" in metrics
        assert "isolated_facility_count" in metrics
        assert "hospital_overload_count" in metrics


@pytest.mark.asyncio
async def test_evaluation_metric_structure(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    metrics = resp.json()["data"]["baseline"]["metrics"]
    for m in metrics:
        assert "name" in m
        assert "unit" in m
        assert "explanation" in m
        # value can be None (undefined metric)
        assert "value" in m


@pytest.mark.asyncio
async def test_evaluation_has_comparison_note(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    data = resp.json()["data"]
    assert "comparison_note" in data
    assert len(data["comparison_note"]) > 20
    # Disclaimer must be in the note
    assert "DISCLAIMER" in data["comparison_note"] or "simulated" in data["comparison_note"].lower()


@pytest.mark.asyncio
async def test_evaluation_has_ran_at(async_client, sample_scenario):
    body = {"scenario_input": sample_scenario, "objective_lambda": 0.3, "objective_mu": 0.1}
    resp = await async_client.post("/api/v1/evaluations/compare", json=body)
    data = resp.json()["data"]
    assert "ran_at" in data


@pytest.mark.asyncio
async def test_evaluation_invalid_body(async_client):
    resp = await async_client.post("/api/v1/evaluations/compare", json={"bad": "input"})
    assert resp.status_code == 422
