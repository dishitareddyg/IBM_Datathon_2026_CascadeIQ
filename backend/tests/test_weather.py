"""
tests/test_weather.py
---------------------
Tests for the weather data endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_weather_current_200(async_client):
    resp = await async_client.get("/api/v1/weather/current")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_weather_current_returns_list(async_client):
    resp = await async_client.get("/api/v1/weather/current")
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_weather_current_observation_structure(async_client):
    resp = await async_client.get("/api/v1/weather/current")
    observations = resp.json()
    if observations:
        obs = observations[0]
        assert "station_id" in obs
        assert "rainfall_mm_1h" in obs
        assert "source" in obs
        assert obs["source"] == "SYNTHETIC"


@pytest.mark.asyncio
async def test_weather_warnings_200(async_client):
    resp = await async_client.get("/api/v1/weather/warnings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_weather_warnings_returns_list(async_client):
    resp = await async_client.get("/api/v1/weather/warnings")
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_weather_status_200(async_client):
    resp = await async_client.get("/api/v1/weather/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_weather_status_has_disclaimer(async_client):
    resp = await async_client.get("/api/v1/weather/status")
    data = resp.json()
    assert "disclaimer" in data
    assert len(data["disclaimer"]) > 10


@pytest.mark.asyncio
async def test_weather_status_freshness_field(async_client):
    resp = await async_client.get("/api/v1/weather/status")
    data = resp.json()
    assert "data_freshness" in data
