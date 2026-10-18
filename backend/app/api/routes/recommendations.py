"""POST /api/v1/recommendations"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import ScenarioNotFoundError
from app.repositories.scenario_repository import scenario_repo
from app.schemas.common import SuccessResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResult
from app.services.intervention_service import intervention_service

router = APIRouter()


@router.post("", response_model=SuccessResponse[RecommendationResult])
@router.post("/", response_model=SuccessResponse[RecommendationResult], include_in_schema=False)
async def create_recommendations(body: RecommendationRequest) -> SuccessResponse[RecommendationResult]:
    runtime = scenario_repo.get_runtime(body.simulation_id)
    if runtime is None:
        raise ScenarioNotFoundError(body.simulation_id)
    result = intervention_service.recommend(
        runtime["state"],
        runtime["assignments"],
        objective_lambda=body.objective_lambda,
        objective_mu=body.objective_mu,
        max_recommendations=body.max_recommendations,
    )
    result.simulation_id = body.simulation_id
    return SuccessResponse(
        data=result,
        metadata={
            "total_candidates": len(result.ranked_interventions),
            "feasible_count": sum(1 for a in result.ranked_interventions if a.feasible),
        },
    )
