"""Fair baseline vs CascadeIQ comparison on identical seeded inputs."""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone

from app.schemas.evaluation import (
    EvaluationMetric,
    EvaluationRequest,
    EvaluationResponse,
    PolicyResult,
)
from app.schemas.simulation import SimulationResult
from app.services.intervention_service import intervention_service
from app.services.simulation_service import simulation_service


def _times(result: SimulationResult) -> list[float]:
    return [a.estimated_arrival_s for a in result.final_assignments]


def _mean_rt(result: SimulationResult) -> EvaluationMetric:
    times = _times(result)
    if not times:
        return EvaluationMetric(
            name="mean_response_time_s",
            value=None,
            unit="seconds",
            denominator=0,
            explanation=(
                "Undefined: mean is over completed ambulance-to-hospital assignments "
                "(denominator = number of feasible assignments). None were feasible."
            ),
        )
    return EvaluationMetric(
        name="mean_response_time_s",
        value=round(statistics.mean(times), 2),
        unit="seconds",
        denominator=len(times),
        explanation=(
            "Mean simulated travel time (ambulance origin → scene → hospital) "
            f"over {len(times)} feasible assignments. Unit: seconds."
        ),
    )


def _p90_rt(result: SimulationResult) -> EvaluationMetric:
    times = sorted(_times(result))
    if len(times) < 5:
        return EvaluationMetric(
            name="p90_response_time_s",
            value=None,
            unit="seconds",
            denominator=len(times),
            explanation=(
                "Undefined: 90th percentile requires at least 5 feasible assignments "
                f"(have {len(times)}). Denominator would be the feasible-assignment count."
            ),
        )
    # Nearest-rank percentile
    idx = max(0, min(len(times) - 1, int(round(0.9 * (len(times) - 1)))))
    return EvaluationMetric(
        name="p90_response_time_s",
        value=round(times[idx], 2),
        unit="seconds",
        denominator=len(times),
        explanation="90th percentile of simulated assignment travel times (seconds).",
    )


def _unreachable(result: SimulationResult, total_requests: int) -> EvaluationMetric:
    assigned = {a.request_id for a in result.final_assignments}
    # Prefer final-step residual list
    final = result.steps[-1].unreachable_requests if result.steps else []
    count = len(final)
    return EvaluationMetric(
        name="unreachable_count",
        value=float(count),
        unit="count",
        denominator=total_requests,
        explanation=(
            f"Count of emergency requests with no feasible ambulance-hospital path at the final step. "
            f"Denominator = {total_requests} requests in the shared initial state."
        ),
    )


def _isolated(result: SimulationResult, n_hospitals: int) -> EvaluationMetric:
    ids = result.steps[-1].isolated_facilities if result.steps else []
    return EvaluationMetric(
        name="isolated_facility_count",
        value=float(len(ids)),
        unit="count",
        denominator=n_hospitals,
        explanation=(
            "Hospitals with no passable path from current ambulance/request nodes at the final step. "
            f"Denominator = {n_hospitals} hospitals in the shared initial state."
        ),
    )


def _overload(result: SimulationResult, n_hospitals: int, threshold: float = 0.9) -> EvaluationMetric:
    loads = result.steps[-1].hospital_loads if result.steps else {}
    n = sum(1 for load in loads.values() if load >= threshold)
    return EvaluationMetric(
        name="hospital_overload_count",
        value=float(n),
        unit="count",
        denominator=n_hospitals,
        explanation=(
            f"Hospitals with simulated occupancy ≥ {threshold:.0%} at the final step. "
            "Occupancy = occupied_beds / total_beds. Not observed census."
        ),
    )


def _latency(ms: float) -> EvaluationMetric:
    return EvaluationMetric(
        name="recommendation_computation_latency_ms",
        value=round(ms, 2),
        unit="milliseconds",
        denominator=1,
        explanation="Wall-clock time to score intervention candidates for this policy run.",
    )


def _metrics(result: SimulationResult, rec_latency_ms: float, n_requests: int, n_hospitals: int) -> list[EvaluationMetric]:
    return [
        _mean_rt(result),
        _p90_rt(result),
        _unreachable(result, n_requests),
        _isolated(result, n_hospitals),
        _overload(result, n_hospitals),
        _latency(rec_latency_ms),
    ]


def _note(baseline: PolicyResult, cascadeiq: PolicyResult) -> str:
    def val(policy: PolicyResult, name: str) -> float | None:
        for metric in policy.metrics:
            if metric.name == name:
                return metric.value
        return None

    parts: list[str] = []
    b_mean, c_mean = val(baseline, "mean_response_time_s"), val(cascadeiq, "mean_response_time_s")
    if b_mean is None or c_mean is None:
        parts.append("Mean response time could not be compared because at least one policy had no feasible assignments.")
    elif b_mean == c_mean:
        parts.append("Both policies produced the same mean simulated response time.")
    elif c_mean < b_mean:
        parts.append(
            f"CascadeIQ mean simulated response time was {b_mean - c_mean:.1f}s lower than baseline on this seed."
        )
    else:
        parts.append(
            f"Baseline mean simulated response time was {c_mean - b_mean:.1f}s lower than CascadeIQ on this seed."
        )
    parts.append(
        "Figures are simulated, computed on identical initial states and seeds. "
        "No operational performance claim is made. Improvements are not invented when metrics are undefined."
    )
    return " ".join(parts)


class EvaluationService:
    def compare(self, body: EvaluationRequest) -> EvaluationResponse:
        scenario = body.scenario_input
        n_requests = len(scenario.emergency_requests)
        n_hospitals = len(scenario.hospitals)

        baseline_result, baseline_state, baseline_asg = simulation_service.run(
            scenario, policy="baseline", persist=True
        )
        t0 = time.perf_counter()
        baseline_recs = intervention_service.recommend(
            baseline_state,
            baseline_asg,
            objective_lambda=body.objective_lambda,
            objective_mu=body.objective_mu,
            max_recommendations=5,
        )
        baseline_latency = (time.perf_counter() - t0) * 1000

        cascade_result, cascade_state, cascade_asg = simulation_service.run(
            scenario, policy="cascadeiq", persist=True
        )
        t1 = time.perf_counter()
        cascade_recs = intervention_service.recommend(
            cascade_state,
            cascade_asg,
            objective_lambda=body.objective_lambda,
            objective_mu=body.objective_mu,
            max_recommendations=5,
        )
        cascade_latency = (time.perf_counter() - t1) * 1000
        _ = baseline_recs, cascade_recs

        baseline_policy = PolicyResult(
            policy_name="baseline",
            metrics=_metrics(baseline_result, baseline_latency, n_requests, n_hospitals),
            simulation_id=baseline_result.simulation_id,
        )
        cascade_policy = PolicyResult(
            policy_name="cascadeiq",
            metrics=_metrics(cascade_result, cascade_latency, n_requests, n_hospitals),
            simulation_id=cascade_result.simulation_id,
        )
        return EvaluationResponse(
            baseline=baseline_policy,
            cascadeiq=cascade_policy,
            comparison_note=_note(baseline_policy, cascade_policy),
            ran_at=datetime.now(timezone.utc),
        )


evaluation_service = EvaluationService()
