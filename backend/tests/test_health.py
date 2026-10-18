"""
tests/test_health.py
--------------------
Tests for the /health liveness probe endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_has_required_fields(async_client):
    response = await async_client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "graph_loaded" in data
    assert "study_area" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_graph_loaded(async_client):
    """Bundled graph must be loaded at test time."""
    response = await async_client.get("/health")
    data = response.json()
    assert data["graph_loaded"] is True


@pytest.mark.asyncio
async def test_health_study_area(async_client):
    response = await async_client.get("/health")
    data = response.json()
    assert "Bengaluru" in data["study_area"]
