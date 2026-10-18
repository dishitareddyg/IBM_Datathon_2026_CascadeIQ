"""
app/schemas/evaluation.py
──────────────────────────
Pydantic v2 schemas for policy evaluation and comparison.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.scenario import ScenarioInput


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── Evaluation Metric ──────────────────────────────────────────────────────────
class EvaluationMetric(_Base):
    """
    A single quantitative metric produced by a policy evaluation run.

    ``value`` may be None when the metric could not be computed (e.g., no
    feasible assignments existed, making average response time undefined).
    ``denominator`` records the population size used for normalisation so
    that clients can display percentages correctly.
    """

    name: str = Field(
        ...,
        description="Machine-readable metric name (e.g., 'avg_response_time_s', 'coverage_rate').",
    )
    value: float | None = Field(
        ...,
        description="Computed metric value. None if the metric is undefined for this run.",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement (e.g., 'seconds', 'ratio', 'count', '%').",
    )
    denominator: int | None = Field(
        default=None,
        description="Denominator used for rate/ratio metrics (e.g., total emergency requests).",
    )
    explanation: str = Field(
        ...,
        description="Plain-language explanation of what this metric measures.",
    )


# ── Policy Result ──────────────────────────────────────────────────────────────
class PolicyResult(_Base):
    """
    Aggregated evaluation metrics for one dispatch policy over one scenario.

    ``policy_name`` identifies the strategy evaluated:
    - ``"baseline"``    — Nearest-ambulance, ignore disruptions.
    - ``"cascadeiq"``   — CascadeIQ cascade-aware optimiser.
    """

    policy_name: str = Field(
        ...,
        description="Human-readable name of the dispatch policy (e.g., 'baseline', 'cascadeiq').",
    )
    metrics: list[EvaluationMetric] = Field(
        default_factory=list,
        description="Ordered list of evaluation metrics for this policy.",
    )
    simulation_id: str = Field(
        ...,
        description="ID of the simulation run that produced these metrics.",
    )


# ── Evaluation Request ─────────────────────────────────────────────────────────
class EvaluationRequest(_Base):
    """
    Body for POST /api/v1/evaluate.

    The backend will execute two simulation runs for the given scenario —
    one with the baseline policy and one with the CascadeIQ policy — and
    return a side-by-side comparison.
    """

    scenario_input: ScenarioInput = Field(
        ...,
        description="Full scenario definition to evaluate both policies against.",
    )
    objective_lambda: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="λ — coverage weight used in the CascadeIQ objective function.",
    )
    objective_mu: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="μ — isolation-penalty weight used in the CascadeIQ objective function.",
    )


# ── Evaluation Response ────────────────────────────────────────────────────────
class EvaluationResponse(_Base):
    """
    Side-by-side policy comparison returned by POST /api/v1/evaluate.

    ``comparison_note`` provides a brief narrative interpretation of the
    relative performance gap between the two policies.
    """

    baseline: PolicyResult = Field(
        ...,
        description="Evaluation results for the nearest-ambulance baseline policy.",
    )
    cascadeiq: PolicyResult = Field(
        ...,
        description="Evaluation results for the CascadeIQ cascade-aware policy.",
    )
    comparison_note: str = Field(
        ...,
        description=(
            "Auto-generated narrative comparing the two policies "
            "(e.g., 'CascadeIQ reduced average response time by 23% and eliminated 2 isolated facilities.')."
        ),
    )
    ran_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp at which this evaluation was completed.",
    )
