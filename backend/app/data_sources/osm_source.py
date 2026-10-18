"""
OSMnx-based road network fetcher for Bengaluru Urban district.

This module downloads, enriches, and converts an OpenStreetMap driving network
into the :class:`~app.models.graph.CityGraph` domain model used throughout
CascadeIQ.

Design decisions
----------------
* **Dual CRS storage**: the raw graph is projected to UTM Zone 43 N
  (EPSG:32643) for accurate metric distance calculation, but node coordinates
  stored in :class:`~app.models.graph.RoadNode` are always WGS 84 (EPSG:4326)
  for compatibility with the geospatial API layer.
* **Edge IDs**: generated deterministically as ``"{u}_{v}_{key}"`` matching
  the OSMnx multi-digraph convention.
* **Speed/travel-time attribution**: OSMnx ``add_edge_speeds`` /
  ``add_edge_travel_times`` are used first; a manual fallback mapping is
  applied for any remaining edges without speed data.
* **Oneway**: the OSM ``oneway`` tag is preserved; OSMnx handles conversion
  of bidirectional edges into opposing directed pairs during download.
* **``is_available``**: always ``True`` — OSM data is freely accessible via
  the Overpass API embedded in OSMnx.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.data_sources.base import DataSource
from app.models.graph import CityGraph, RoadEdge, RoadNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Road-type → default speed (km/h) mapping
# Source: OpenStreetMap wiki (highway tag), Karnataka PWD speed limits,
#         and Bengaluru Traffic Police advisories.
# ---------------------------------------------------------------------------
_ROAD_TYPE_SPEED: dict[str, float] = {
    "motorway": 80.0,
    "motorway_link": 60.0,
    "trunk": 80.0,
    "trunk_link": 60.0,
    "primary": 60.0,
    "primary_link": 50.0,
    "secondary": 50.0,
    "secondary_link": 40.0,
    "tertiary": 40.0,
    "tertiary_link": 35.0,
    "residential": 30.0,
    "living_street": 20.0,
    "service": 20.0,
    "unclassified": 25.0,
}
_DEFAULT_SPEED_KMH: float = 25.0

# Flood risk defaults per road type (0.0–1.0).
# Lower roads, underpasses, and service lanes have higher flood risk.
# These are heuristic defaults; real values come from flood-model overlays.
_ROAD_FLOOD_RISK: dict[str, float] = {
    "motorway": 0.05,
    "motorway_link": 0.10,
    "trunk": 0.08,
    "trunk_link": 0.12,
    "primary": 0.15,
    "primary_link": 0.18,
    "secondary": 0.20,
    "secondary_link": 0.22,
    "tertiary": 0.25,
    "tertiary_link": 0.28,
    "residential": 0.35,
    "living_street": 0.40,
    "service": 0.45,
    "unclassified": 0.30,
}
_DEFAULT_FLOOD_RISK: float = 0.30


class OSMDataSource(DataSource):
    """
    Fetches and converts an OSMnx road network into a :class:`CityGraph`.

    Usage
    -----
    ::

        source = OSMDataSource()
        city_graph = await source.fetch_graph(
            bbox=(12.75, 77.35, 13.18, 77.85),
            network_type="drive",
        )
    """

    def __init__(self) -> None:
        self._cached_graph: Optional[CityGraph] = None

    # ------------------------------------------------------------------
    # DataSource interface (weather methods are no-ops for OSM source)
    # ------------------------------------------------------------------

    @property
    def source_name(self) -> str:
        return "OSM"

    @property
    def is_available(self) -> bool:
        """OSM via OSMnx / Overpass API is always available (requires internet)."""
        return True

    async def fetch_rainfall(self, bbox: tuple) -> list[dict]:
        """Not applicable for OSM source — returns empty list."""
        return []

    async def fetch_warnings(self, district: str) -> list[dict]:
        """Not applicable for OSM source — returns empty list."""
        return []

    # ------------------------------------------------------------------
    # Primary graph fetch
    # ------------------------------------------------------------------

    async def fetch_graph(
        self,
        bbox: tuple,
        network_type: str = "drive",
        use_cache: bool = True,
    ) -> Optional[CityGraph]:
        """
        Download, enrich, and return a :class:`CityGraph` for *bbox*.

        Parameters
        ----------
        bbox:
            ``(min_lat, min_lon, max_lat, max_lon)`` in WGS 84.
        network_type:
            OSMnx network type (``'drive'``, ``'walk'``, …).  Defaults to
            ``'drive'`` for emergency-vehicle routing.
        use_cache:
            If ``True`` and a graph was previously fetched, return the cached
            instance immediately.

        Returns
        -------
        CityGraph or None
            ``None`` if the download fails (network unavailable, Overpass
            timeout, etc.).  Callers should fall back to a synthetic graph.
        """
        if use_cache and self._cached_graph is not None:
            logger.info("OSMDataSource: returning cached CityGraph.")
            return self._cached_graph

        try:
            import osmnx as ox  # noqa: PLC0415
        except ImportError:
            logger.error(
                "osmnx is not installed. Install it with: pip install osmnx"
            )
            return None

        try:
            logger.info(
                "OSMDataSource: fetching %s graph for bbox=%s …", network_type, bbox
            )
            min_lat, min_lon, max_lat, max_lon = bbox

            # Download from Overpass API — preserves oneway restrictions.
            from app.core.config import get_settings

            ox.settings.timeout = int(get_settings().osm_timeout_s)
            raw_graph = ox.graph_from_bbox(
                north=max_lat,
                south=min_lat,
                east=max_lon,
                west=min_lon,
                network_type=network_type,
                retain_all=False,
                simplify=True,
            )

            # Enrich with speed and travel-time attributes.
            # OSMnx infers speed from the `maxspeed` OSM tag where available,
            # falling back to its own road-type lookup table.
            raw_graph = ox.add_edge_speeds(raw_graph)
            raw_graph = ox.add_edge_travel_times(raw_graph)

            # Project to UTM 43 N for metric accuracy.
            projected_graph = ox.project_graph(raw_graph, to_crs="EPSG:32643")

            city_graph = self._convert_to_city_graph(
                raw_graph=raw_graph,
                projected_graph=projected_graph,
                bbox=bbox,
            )
            self._cached_graph = city_graph
            logger.info(
                "OSMDataSource: graph built — %d nodes, %d edges.",
                city_graph.node_count(),
                city_graph.edge_count(),
            )
            return city_graph

        except Exception as exc:
            logger.error("OSMDataSource: graph fetch failed — %s", exc, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def _convert_to_city_graph(
        self,
        raw_graph,          # networkx.MultiDiGraph (WGS 84)
        projected_graph,    # networkx.MultiDiGraph (UTM 43 N)
        bbox: tuple,
    ) -> CityGraph:
        """Convert OSMnx multi-digraphs into a :class:`CityGraph`."""
        import networkx as nx  # noqa: PLC0415

        nodes: dict[str, RoadNode] = {}
        edges: dict[str, RoadEdge] = {}
        routing_graph = nx.DiGraph()

        # ----------------------------------------------------------
        # Nodes — coordinates from WGS 84 graph
        # ----------------------------------------------------------
        for node_id, data in raw_graph.nodes(data=True):
            lat = float(data.get("y", 0.0))
            lon = float(data.get("x", 0.0))
            node_type = "intersection"
            if data.get("highway") in ("bus_stop",):
                node_type = "facility"
            nodes[str(node_id)] = RoadNode(
                node_id=str(node_id),
                lat=lat,
                lon=lon,
                node_type=node_type,
                metadata={k: v for k, v in data.items() if k not in ("x", "y")},
            )
            routing_graph.add_node(str(node_id), lat=lat, lon=lon)

        # ----------------------------------------------------------
        # Edges — lengths from projected (UTM 43 N) graph for accuracy
        # ----------------------------------------------------------
        proj_edge_lengths: dict[tuple, float] = {}
        for u, v, key, data in projected_graph.edges(keys=True, data=True):
            length = float(data.get("length", 0.0))
            proj_edge_lengths[(u, v, key)] = length

        for u, v, key, data in raw_graph.edges(keys=True, data=True):
            edge_id = f"{u}_{v}_{key}"
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0]
            road_type = str(highway)

            # Length: prefer projected metric value
            length_m = float(
                proj_edge_lengths.get((u, v, key), data.get("length", 0.0))
            )

            # Speed: OSMnx-enriched value, then road-type lookup, then default
            speed_kmh = float(
                data.get("speed_kph")
                or data.get("maxspeed_kph")
                or _ROAD_TYPE_SPEED.get(road_type, _DEFAULT_SPEED_KMH)
            )

            # Travel time: re-compute from our length + speed for consistency
            travel_time_s = length_m / (speed_kmh / 3.6) if speed_kmh > 0 else 9999.0

            oneway = bool(data.get("oneway", False))
            flood_risk = _ROAD_FLOOD_RISK.get(road_type, _DEFAULT_FLOOD_RISK)

            road_edge = RoadEdge(
                edge_id=edge_id,
                source=str(u),
                target=str(v),
                length_m=round(length_m, 2),
                road_type=road_type,
                status="OPEN",
                speed_kmh=round(speed_kmh, 1),
                travel_time_s=round(travel_time_s, 2),
                oneway=oneway,
                flood_risk=round(flood_risk, 3),
                metadata={
                    "osmid": data.get("osmid"),
                    "name": data.get("name"),
                    "lanes": data.get("lanes"),
                    "surface": data.get("surface"),
                    "key": key,
                },
            )
            edges[edge_id] = road_edge

            # Add to routing graph with travel_time_s weight
            routing_graph.add_edge(
                str(u),
                str(v),
                edge_id=edge_id,
                weight=travel_time_s,
                travel_time_s=travel_time_s,
                length_m=length_m,
                status="OPEN",
            )

        return CityGraph(
            nodes=nodes,
            edges=edges,
            nx_graph=routing_graph,
            crs="EPSG:4326",
            bbox=bbox,
            source="OSM",
            retrieved_at=datetime.now(timezone.utc),
        )

    def clear_cache(self) -> None:
        """Invalidate the cached graph, forcing a fresh download on next call."""
        self._cached_graph = None
        logger.info("OSMDataSource: graph cache cleared.")
