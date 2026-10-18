"""
Rule-based flood-related road risk.

Rainfall observations and official warnings are not water-depth measurements
on individual roads. This service never marks a road CLOSED solely because a
weather alert exists. CLOSED status is reserved for explicit scenario
disruptions (or later validated field reports).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.models.graph import CityGraph, RoadEdge
from app.models.scenario import RoadDisruption

# Heuristic susceptibility by OSM highway class (not observed inundation).
_ROAD_SUSCEPTIBILITY: dict[str, float] = {
    "motorway": 0.10,
    "trunk": 0.15,
    "primary": 0.25,
    "secondary": 0.35,
    "tertiary": 0.45,
    "residential": 0.55,
    "living_street": 0.60,
    "service": 0.65,
    "unclassified": 0.40,
    "hospital": 0.20,
}


@dataclass(frozen=True)
class WeatherSignals:
    """Separated weather inputs used by the risk rules."""

    rainfall_mm_1h: float
    rainfall_mm_24h: float
    warning_severity_score: float  # 0-1, 0 if no warning
    rainfall_kind: str  # observed | forecast | synthetic
    warning_kind: str  # observed | forecast | synthetic | none


def _rainfall_score(mm_24h: float, settings) -> float:
    if mm_24h <= 0:
        return 0.0
    if mm_24h >= settings.flood_risk_rainfall_mm_critical:
        return 1.0
    if mm_24h >= settings.flood_risk_rainfall_mm_high:
        span = settings.flood_risk_rainfall_mm_critical - settings.flood_risk_rainfall_mm_high
        return 0.6 + 0.4 * min(1.0, (mm_24h - settings.flood_risk_rainfall_mm_high) / max(span, 1e-6))
    return min(0.6, mm_24h / settings.flood_risk_rainfall_mm_high * 0.6)


def composite_risk(edge: RoadEdge, signals: WeatherSignals, settings=None) -> tuple[float, str]:
    """
    Return (score, rationale). Score is inferred, not observed depth.
    """
    settings = settings or get_settings()
    rain = _rainfall_score(signals.rainfall_mm_24h, settings)
    warn = max(0.0, min(1.0, signals.warning_severity_score))
    susceptibility = _ROAD_SUSCEPTIBILITY.get(edge.road_type, 0.40)
    score = (
        settings.flood_risk_rainfall_weight * rain
        + settings.flood_risk_warning_weight * warn
    ) * (0.5 + 0.5 * susceptibility)
    score = max(0.0, min(1.0, score))
    rationale = (
        f"inferred_risk={score:.2f} from {signals.rainfall_kind} 24h rainfall "
        f"{signals.rainfall_mm_24h:.1f} mm (score={rain:.2f}) and {signals.warning_kind} "
        f"warning score {warn:.2f}; road_type={edge.road_type} susceptibility={susceptibility:.2f}. "
        "This is not an observation of water depth on the segment."
    )
    return score, rationale


class RiskService:
    def apply_inferred_risk(self, graph: CityGraph, signals: WeatherSignals) -> list[str]:
        """
        Mark high-risk OPEN roads as DEGRADED using configurable rules.

        Never sets CLOSED. Returns edge ids that changed.
        """
        settings = get_settings()
        changed: list[str] = []
        for edge in graph.edges.values():
            if edge.status == "CLOSED":
                continue
            score, rationale = composite_risk(edge, signals, settings)
            edge.flood_risk = max(edge.flood_risk, score)
            edge.metadata = {
                **(edge.metadata or {}),
                "inferred_risk": score,
                "inferred_rationale": rationale,
                "value_kind": "inferred",
            }
            if (
                score >= settings.inferred_degrade_threshold
                and signals.rainfall_mm_24h >= settings.flood_risk_rainfall_mm_high
                and edge.status == "OPEN"
            ):
                edge.status = "DEGRADED"
                self._sync_nx(graph, edge)
                changed.append(edge.edge_id)
            else:
                self._sync_nx(graph, edge)
        return changed

    def apply_scenario_disruptions(self, graph: CityGraph, disruptions: list[RoadDisruption]) -> list[str]:
        applied: list[str] = []
        for disruption in disruptions:
            edge = graph.edges.get(disruption.edge_id)
            if edge is None:
                continue
            if disruption.status not in ("OPEN", "DEGRADED", "CLOSED"):
                continue
            edge.status = disruption.status
            edge.flood_risk = max(edge.flood_risk, disruption.severity)
            edge.metadata = {
                **(edge.metadata or {}),
                "confidence": disruption.confidence,
                "cause": disruption.cause,
                "estimated_by": disruption.estimated_by,
                "value_kind": "scenario",
            }
            self._sync_nx(graph, edge)
            applied.append(edge.edge_id)
        return applied

    def _sync_nx(self, graph: CityGraph, edge: RoadEdge) -> None:
        settings = get_settings()
        if not graph.nx_graph.has_edge(edge.source, edge.target):
            return
        data = graph.nx_graph[edge.source][edge.target]
        data["status"] = edge.status
        data["flood_risk"] = edge.flood_risk
        if edge.status == "DEGRADED":
            severity = max(edge.flood_risk, 0.0)
            data["travel_time_s"] = edge.travel_time_s * (1.0 + severity * (settings.degraded_travel_time_multiplier_max - 1.0))
        else:
            data["travel_time_s"] = edge.travel_time_s
        data["weight"] = data["travel_time_s"]


risk_service = RiskService()
