"""Weather endpoints. All Phase-1 values are synthetic unless IMD is configured."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.weather import RainfallObservation, WeatherStatus, WeatherWarning
from app.services.weather_service import weather_service

router = APIRouter()


@router.get("/current", response_model=list[RainfallObservation])
async def current_weather(seed: int = Query(default=42)) -> list[RainfallObservation]:
    return await weather_service.observations(seed=seed)


@router.get("/warnings", response_model=list[WeatherWarning])
async def weather_warnings(seed: int = Query(default=42)) -> list[WeatherWarning]:
    return await weather_service.warnings(seed=seed)


@router.get("/status", response_model=WeatherStatus)
async def weather_status(seed: int = Query(default=42)) -> WeatherStatus:
    return await weather_service.status(seed=seed)
