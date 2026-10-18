"""Shared pytest fixtures. No network and no API credentials required."""

from __future__ import annotations

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("USE_BUNDLED_GRAPH", "true")


@pytest.fixture(scope="session", autouse=True)
def bundled_graph():
    from app.services.graph_service import graph_service

    graph_service.load_bundled()
    return graph_service.get()


@pytest.fixture
async def async_client(bundled_graph):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sample_scenario() -> dict:
    return {
        "scenario_id": "test_scenario_conftest",
        "seed": 42,
        "hospitals": [
            {
                "hospital_id": "H1",
                "name": "Victoria Hospital",
                "lat": 12.9612,
                "lon": 77.5726,
                "total_beds": 200,
                "available_beds": 80,
                "icu_beds": 20,
            },
            {
                "hospital_id": "H2",
                "name": "Manipal Hospital",
                "lat": 12.9399,
                "lon": 77.6180,
                "total_beds": 300,
                "available_beds": 150,
                "icu_beds": 30,
            },
        ],
        "ambulances": [
            {"ambulance_id": "A1", "lat": 12.9767, "lon": 77.5713, "is_available": True},
            {"ambulance_id": "A2", "lat": 12.9279, "lon": 77.6271, "is_available": True},
        ],
        "emergency_requests": [
            {
                "request_id": "R1",
                "origin_lat": 12.9500,
                "origin_lon": 77.5900,
                "priority": "HIGH",
            },
            {
                "request_id": "R2",
                "origin_lat": 12.9800,
                "origin_lon": 77.6000,
                "priority": "CRITICAL",
            },
        ],
        "road_disruptions": [],
        "simulation_steps": 5,
        "weather_mode": "synthetic",
    }


@pytest.fixture
def sample_scenario_with_disruptions(sample_scenario) -> dict:
    sc = copy.deepcopy(sample_scenario)
    sc["scenario_id"] = "test_scenario_disrupted"
    sc["road_disruptions"] = [
        {
            "edge_id": "majestic_richmond_circle",
            "status": "CLOSED",
            "severity": 1.0,
            "confidence": 0.9,
            "cause": "Flooding (scenario, not observed depth)",
            "estimated_by": "scenario",
        }
    ]
    return sc
