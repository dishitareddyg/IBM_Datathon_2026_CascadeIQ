"""City metadata and compact graph."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import GraphNotLoadedError
from app.schemas.city import CityGraphResponse, CityMetadataResponse
from app.services.city_service import city_service
from app.services.graph_service import graph_service

router = APIRouter()


@router.get("/metadata", response_model=CityMetadataResponse)
async def get_city_metadata() -> CityMetadataResponse:
    return city_service.metadata()


@router.get("/graph", response_model=CityGraphResponse)
async def get_city_graph() -> CityGraphResponse:
    if not graph_service.loaded:
        raise GraphNotLoadedError()
    return city_service.compact_graph()
