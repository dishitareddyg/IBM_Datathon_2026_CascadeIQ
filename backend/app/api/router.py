"""Mount versioned REST routes under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import city, evaluations, recommendations, scenarios, simulations, weather

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(city.router, prefix="/city", tags=["City Graph"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Simulation"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluation"])
