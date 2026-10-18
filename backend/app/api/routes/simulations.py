"""Simulation create/retrieve/cascade."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import ScenarioNotFoundError, ValidationError
from app.schemas.common import SuccessResponse
from app.schemas.scenario import ScenarioInput
from app.schemas.simulation import CascadeStep, SimulationResult
from app.repositories.scenario_repository import scenario_repo
from app.services.simulation_service import simulation_service

router = APIRouter()


@router.post("", response_model=SuccessResponse[SimulationResult], status_code=201)
@router.post("/", response_model=SuccessResponse[SimulationResult], status_code=201, include_in_schema=False)
@router.post("/run", response_model=SuccessResponse[SimulationResult], status_code=201, include_in_schema=False)
async def create_simulation(scenario: ScenarioInput) -> SuccessResponse[SimulationResult]:
    result, _, _ = simulation_service.run(scenario, policy="cascadeiq", persist=True)
    return SuccessResponse(data=result, metadata={"simulation_id": result.simulation_id, "policy": "cascadeiq"})


@router.get("", response_model=SuccessResponse[list[str]])
@router.get("/", response_model=SuccessResponse[list[str]], include_in_schema=False)
async def list_simulations() -> SuccessResponse[list[str]]:
    ids = scenario_repo.list_ids()
    return SuccessResponse(data=ids, metadata={"count": len(ids)})


@router.get("/{simulation_id}", response_model=SuccessResponse[SimulationResult])
async def get_simulation(simulation_id: str) -> SuccessResponse[SimulationResult]:
    result = scenario_repo.get_sync(simulation_id)
    if result is None:
        raise ScenarioNotFoundError(simulation_id)
    return SuccessResponse(data=result)


@router.get("/{simulation_id}/cascade", response_model=SuccessResponse[list[CascadeStep]])
async def get_cascade(
    simulation_id: str,
    step: int | None = Query(default=None, ge=0),
) -> SuccessResponse[list[CascadeStep]]:
    result = scenario_repo.get_sync(simulation_id)
    if result is None:
        raise ScenarioNotFoundError(simulation_id)
    steps = result.steps
    if step is not None:
        steps = [s for s in steps if s.step_index == step]
        if not steps:
            raise ValidationError(f"Step {step} is not present in simulation {simulation_id}.", field="step")
    return SuccessResponse(
        data=steps,
        metadata={
            "simulation_id": simulation_id,
            "disclaimer": "Cascade timeline is simulated, not an incident log.",
        },
    )
