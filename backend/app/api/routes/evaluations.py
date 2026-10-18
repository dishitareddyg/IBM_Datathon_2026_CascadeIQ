"""POST /api/v1/evaluations/compare"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import SuccessResponse
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services.evaluation_service import evaluation_service

router = APIRouter()


@router.post("/compare", response_model=SuccessResponse[EvaluationResponse])
async def compare_policies(body: EvaluationRequest) -> SuccessResponse[EvaluationResponse]:
    response = evaluation_service.compare(body)
    return SuccessResponse(
        data=response,
        metadata={
            "baseline_simulation_id": response.baseline.simulation_id,
            "cascadeiq_simulation_id": response.cascadeiq.simulation_id,
            "total_requests": len(body.scenario_input.emergency_requests),
            "fairness": "Identical ScenarioInput, including seed, requests, resources and disruptions.",
        },
    )
