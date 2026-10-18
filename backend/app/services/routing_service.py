"""Dijkstra routing on the passable (OPEN + DEGRADED) subgraph."""

from __future__ import annotations

from typing import Optional

import networkx as nx

from app.models.entities import RouteResult
from app.models.graph import CityGraph
from app.utils.geo import snap_to_nearest_node, validate_crs
from app.core.config import get_settings


class RoutingService:
    def snap(self, graph: CityGraph, lat: float, lon: float) -> Optional[str]:
        return snap_to_nearest_node(lat, lon, graph.nx_graph)

    def shortest_path(self, graph: CityGraph, source: str, target: str) -> RouteResult:
        """
        Shortest feasible path by travel_time_s. CLOSED edges are excluded.
        """
        if source not in graph.nodes or target not in graph.nodes:
            return RouteResult(
                source_node=source,
                target_node=target,
                path_nodes=[],
                edge_ids=[],
                total_distance_m=0.0,
                total_time_s=0.0,
                is_feasible=False,
                infeasibility_reason="Origin or destination node is not in the city graph.",
            )
        passable = graph.get_passable_graph()
        if source not in passable or target not in passable:
            return RouteResult(
                source_node=source,
                target_node=target,
                path_nodes=[],
                edge_ids=[],
                total_distance_m=0.0,
                total_time_s=0.0,
                is_feasible=False,
                infeasibility_reason="Origin or destination is not in the passable graph.",
            )
        try:
            path = nx.shortest_path(passable, source, target, weight="travel_time_s")
        except nx.NetworkXNoPath:
            return RouteResult(
                source_node=source,
                target_node=target,
                path_nodes=[],
                edge_ids=[],
                total_distance_m=0.0,
                total_time_s=0.0,
                is_feasible=False,
                infeasibility_reason="No passable path: remaining OPEN/DEGRADED edges do not connect the nodes.",
            )

        edge_ids: list[str] = []
        distance = 0.0
        time_s = 0.0
        for u, v in zip(path, path[1:]):
            data = passable[u][v]
            edge_ids.append(str(data.get("edge_id", f"{u}_{v}")))
            distance += float(data.get("length_m", 0.0))
            time_s += float(data.get("travel_time_s", 0.0))
        return RouteResult(
            source_node=source,
            target_node=target,
            path_nodes=path,
            edge_ids=edge_ids,
            total_distance_m=round(distance, 1),
            total_time_s=round(time_s, 1),
            is_feasible=True,
        )

    def nearest_reachable(
        self,
        graph: CityGraph,
        origin: str,
        candidates: list[str],
        *,
        excluded: set[str] | None = None,
    ) -> tuple[Optional[str], RouteResult]:
        excluded = excluded or set()
        best_id: Optional[str] = None
        best: Optional[RouteResult] = None
        for candidate in candidates:
            if candidate in excluded:
                continue
            result = self.shortest_path(graph, origin, candidate)
            if not result.is_feasible:
                continue
            if best is None or result.total_time_s < best.total_time_s:
                best = result
                best_id = candidate
        if best is None or best_id is None:
            return None, RouteResult(
                source_node=origin,
                target_node="",
                path_nodes=[],
                edge_ids=[],
                total_distance_m=0.0,
                total_time_s=0.0,
                is_feasible=False,
                infeasibility_reason="No reachable candidate on the passable graph.",
            )
        return best_id, best

    def is_reachable(self, graph: CityGraph, source: str, target: str) -> bool:
        return self.shortest_path(graph, source, target).is_feasible

    def projected_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Metric distance after validating CRS (UTM 43N)."""
        from app.utils.geo import projected_distance_m

        settings = get_settings()
        validate_crs(settings.coordinate_system, settings.local_crs)
        return projected_distance_m(lat1, lon1, lat2, lon2, settings.coordinate_system, settings.local_crs)


routing_service = RoutingService()
