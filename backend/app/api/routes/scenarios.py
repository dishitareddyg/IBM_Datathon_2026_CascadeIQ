"""
app/api/routes/scenarios.py
───────────────────────────
Endpoints for listing and retrieving bundled scenario configurations.

GET /api/v1/scenarios           — List all bundled scenarios.
GET /api/v1/scenarios/{id}     — Get a single bundled scenario by ID.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.common import SuccessResponse
from app.schemas.scenario import ScenarioConfig

router = APIRouter()

# ── Bundled scenario catalogue ─────────────────────────────────────────────────
_BUNDLED_SCENARIOS: list[ScenarioConfig] = [
    ScenarioConfig(
        scenario_id="flood_koramangala_2024",
        display_name="Koramangala Flash Flood — 2024",
        description=(
            "Simulates the August 2024 flash-flood event in Koramangala, Bengaluru. "
            "Multiple arterial roads are partially or fully inundated. "
            "Hospitals in the southern corridor experience increased demand "
            "while northern routes remain largely passable."
        ),
        weather_mode="synthetic",
        default_simulation_steps=15,
        tags=["flood", "koramangala", "high-severity", "2024"],
    ),
    ScenarioConfig(
        scenario_id="monsoon_north_blr_moderate",
        display_name="North Bengaluru Moderate Monsoon",
        description=(
            "A moderate monsoon scenario affecting Hebbal, Yelahanka, and Kengeri. "
            "Road degradation is spread across the network rather than concentrated "
            "in a single locality. Tests the system's ability to re-route "
            "across a weakly disrupted graph."
        ),
        weather_mode="synthetic",
        default_simulation_steps=10,
        tags=["monsoon", "north-bengaluru", "moderate"],
    ),
    ScenarioConfig(
        scenario_id="extreme_rainfall_citywide",
        display_name="Extreme Citywide Rainfall — Stress Test",
        description=(
            "A high-severity stress-test scenario in which ≥100 mm/24h rainfall "
            "is recorded across all monitoring stations, triggering CRITICAL flood "
            "risk across the district. Designed to reveal cascade failure patterns "
            "and measure hospital isolation rates."
        ),
        weather_mode="synthetic",
        default_simulation_steps=25,
        tags=["extreme", "stress-test", "citywide", "critical"],
    ),
]

_SCENARIO_INDEX: dict[str, ScenarioConfig] = {s.scenario_id: s for s in _BUNDLED_SCENARIOS}


@router.get(
    "",
    response_model=SuccessResponse[list[ScenarioConfig]],
    summary="List bundled scenarios",
    description="Returns the catalogue of pre-built scenarios shipped with CascadeIQ.",
)
async def list_scenarios() -> SuccessResponse[list[ScenarioConfig]]:
    """Return all bundled scenario configurations."""
    return SuccessResponse(
        data=_BUNDLED_SCENARIOS,
        metadata={"total": len(_BUNDLED_SCENARIOS)},
    )


@router.get(
    "/{scenario_id}",
    response_model=SuccessResponse[ScenarioConfig],
    summary="Get bundled scenario by ID",
)
async def get_scenario(scenario_id: str) -> SuccessResponse[ScenarioConfig]:
    """Return a single bundled scenario configuration."""
    scenario = _SCENARIO_INDEX.get(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundled scenario '{scenario_id}' not found.",
        )
    return SuccessResponse(data=scenario)
