"""
Domain models for the in-memory city road-network graph.

CRS conventions
---------------
* Storage / API      : WGS 84  (EPSG:4326)
* Distance / routing : UTM Zone 43 N (EPSG:32643)
"""

from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import networkx as nx


# ---------------------------------------------------------------------------
# Road primitives
# ---------------------------------------------------------------------------

@dataclass
class RoadNode:
    """A node in the city graph (intersection, hospital entrance, facility gate …)."""
    node_id: str
    lat: float
    lon: float
    node_type: str          # 'intersection' | 'hospital' | 'facility'
    metadata: dict = field(default_factory=dict)


@dataclass
class RoadEdge:
    """A directed edge in the city graph."""
    edge_id: str
    source: str
    target: str
    length_m: float
    road_type: str
    status: str             # 'OPEN' | 'DEGRADED' | 'CLOSED'
    speed_kmh: float
    travel_time_s: float    # computed: length_m / (speed_kmh / 3.6)
    oneway: bool
    flood_risk: float       # 0.0–1.0
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience constructor
    # ------------------------------------------------------------------
    @classmethod
    def from_parts(
        cls,
        edge_id: str,
        source: str,
        target: str,
        length_m: float,
        road_type: str,
        status: str,
        speed_kmh: float,
        oneway: bool,
        flood_risk: float = 0.0,
        metadata: Optional[dict] = None,
    ) -> "RoadEdge":
        travel_time_s = length_m / (speed_kmh / 3.6)
        return cls(
            edge_id=edge_id,
            source=source,
            target=target,
            length_m=length_m,
            road_type=road_type,
            status=status,
            speed_kmh=speed_kmh,
            travel_time_s=travel_time_s,
            oneway=oneway,
            flood_risk=flood_risk,
            metadata=metadata or {},
        )


# ---------------------------------------------------------------------------
# City graph container
# ---------------------------------------------------------------------------

@dataclass
class CityGraph:
    """
    Wraps a NetworkX DiGraph alongside rich metadata for all nodes and edges.

    The ``nx_graph`` attribute is a ``networkx.DiGraph`` where each edge carries
    a ``travel_time_s`` weight attribute used for shortest-path queries.  Only
    OPEN and DEGRADED edges are included in the passable subgraph returned by
    :meth:`get_passable_graph`.
    """

    nodes: dict[str, RoadNode]
    edges: dict[str, RoadEdge]
    nx_graph: Any               # networkx.DiGraph — typed as Any to avoid circular import
    crs: str                    # e.g. 'EPSG:4326'
    bbox: tuple                 # (min_lat, min_lon, max_lat, max_lon)
    source: str                 # 'OSM' | 'SYNTHETIC' | …
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Derived graph accessors
    # ------------------------------------------------------------------

    def get_passable_graph(self) -> nx.DiGraph:
        """Return a subgraph that excludes all CLOSED edges.

        DEGRADED edges are included but their ``travel_time_s`` weights remain
        unmodified here; callers should apply :meth:`get_degraded_travel_time`
        when computing actual routing costs.
        """
        closed_edges = {
            (e.source, e.target)
            for e in self.edges.values()
            if e.status == "CLOSED"
        }
        passable = nx.DiGraph()
        passable.add_nodes_from(self.nx_graph.nodes(data=True))
        for u, v, data in self.nx_graph.edges(data=True):
            if (u, v) not in closed_edges:
                passable.add_edge(u, v, **data)
        return passable

    def get_degraded_travel_time(self, edge_id: str, disruption_severity: float) -> float:
        """Return effective travel time for an edge given a disruption severity.

        Travel time increases linearly up to **3×** at maximum severity.

        Parameters
        ----------
        edge_id:
            Identifier of the edge (must exist in ``self.edges``).
        disruption_severity:
            Float in [0.0, 1.0].  0 ⇒ no change; 1 ⇒ 3× base travel time.

        Returns
        -------
        float
            Effective travel time in seconds.  Returns base travel time if the
            edge is not found.
        """
        edge = self.edges.get(edge_id)
        if edge is None:
            return 0.0
        severity = max(0.0, min(1.0, disruption_severity))
        # Linear interpolation: multiplier goes from 1.0 at sev=0 to 3.0 at sev=1
        multiplier = 1.0 + severity * 2.0
        return edge.travel_time_s * multiplier

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def edge_by_endpoints(self, source: str, target: str) -> Optional[RoadEdge]:
        """Return the first edge matching source→target, or None."""
        for edge in self.edges.values():
            if edge.source == source and edge.target == target:
                return edge
        return None

    def copy(self) -> "CityGraph":
        """Deep-copy nodes, edges and the NetworkX graph so simulations cannot mutate the cache."""
        cloned_nx = self.nx_graph.copy()
        return CityGraph(
            nodes={k: copy(v) for k, v in self.nodes.items()},
            edges={k: copy(v) for k, v in self.edges.items()},
            nx_graph=cloned_nx,
            crs=self.crs,
            bbox=self.bbox,
            source=self.source,
            retrieved_at=self.retrieved_at,
            provenance=deepcopy(self.provenance),
        )

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"CityGraph(nodes={self.node_count()}, edges={self.edge_count()}, "
            f"source='{self.source}', crs='{self.crs}')"
        )
