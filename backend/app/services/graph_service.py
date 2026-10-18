"""
Cached city-graph access for CascadeIQ.

The bundled sample graph is a simplified synthetic representation of
Bengaluru Urban district landmarks. It is NOT a faithful OSM extract and
must not be used for real navigation. Live OSM download is optional, cached
for the process lifetime, and never performed per HTTP request.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx

from app.core.config import get_settings
from app.core.errors import GraphNotLoadedError
from app.models.graph import CityGraph, RoadEdge, RoadNode

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SAMPLE_JSON = _DATA_DIR / "sample_graph.json"
_SAMPLE_GRAPHML = _DATA_DIR / "bengaluru_urban_sample.graphml"

_SPEED_KMPH: dict[str, float] = {
    "motorway": 80.0,
    "trunk": 60.0,
    "primary": 50.0,
    "secondary": 40.0,
    "tertiary": 30.0,
    "residential": 20.0,
    "unclassified": 20.0,
    "service": 15.0,
    "hospital": 15.0,
}

# Landmark nodes inside the Bengaluru Urban envelope (airport/Devanahalli omitted:
# Kempegowda International Airport is in Devanahalli, Bengaluru Rural).
_LANDMARK_NODES: list[tuple] = [
    ("majestic", 12.9767, 77.5713, "intersection"),
    ("silk_board", 12.9172, 77.6234, "intersection"),
    ("hebbal", 13.0351, 77.5967, "intersection"),
    ("whitefield", 12.9698, 77.7499, "intersection"),
    ("electronic_city", 12.8458, 77.6643, "intersection"),
    ("koramangala", 12.9279, 77.6271, "intersection"),
    ("indiranagar", 12.9784, 77.6408, "intersection"),
    ("yelahanka", 13.1007, 77.5963, "intersection"),
    ("marathahalli", 12.9591, 77.7009, "intersection"),
    ("jp_nagar", 12.9102, 77.5826, "intersection"),
    ("richmond_circle", 12.9641, 77.5984, "intersection"),
    ("hsr_layout", 12.9116, 77.6446, "intersection"),
    ("jayanagar", 12.9299, 77.5826, "intersection"),
    ("rajajinagar", 12.9952, 77.5524, "intersection"),
    ("banashankari", 12.9256, 77.5468, "intersection"),
    ("bommanahalli", 12.8904, 77.6359, "intersection"),
    ("whitefield_hub", 12.9806, 77.7301, "intersection"),
    ("kr_puram", 13.0003, 77.6972, "intersection"),
    ("hennur", 13.0333, 77.6327, "intersection"),
    ("btm_layout", 12.9165, 77.6101, "intersection"),
    ("domlur", 12.9603, 77.6391, "intersection"),
    ("mg_road", 12.9754, 77.6060, "intersection"),
    ("nagawara", 13.0441, 77.6202, "intersection"),
    ("tumkur_road", 13.0500, 77.5520, "intersection"),
    ("hosur_road", 12.8700, 77.6500, "intersection"),
    ("old_airport_rd", 12.9652, 77.6494, "intersection"),
    ("bellandur", 12.9254, 77.6699, "intersection"),
    ("sarjapur", 12.8622, 77.7128, "intersection"),
    ("bannerghatta_rd", 12.8748, 77.5978, "intersection"),
    ("ulsoor", 12.9809, 77.6209, "intersection"),
    ("shivajinagar", 12.9858, 77.5999, "intersection"),
    ("frazer_town", 12.9902, 77.6177, "intersection"),
    ("cox_town", 13.0012, 77.6070, "intersection"),
    ("banaswadi", 13.0101, 77.6436, "intersection"),
    ("ramamurthy_nagar", 13.0052, 77.6671, "intersection"),
    ("mahadevapura", 12.9930, 77.7119, "intersection"),
    ("varthur", 12.9387, 77.7411, "intersection"),
    ("victoria_hosp", 12.9612, 77.5726, "hospital"),
    ("manipal_hosp", 12.9399, 77.6180, "hospital"),
    ("fortis_banner", 12.8748, 77.5978, "hospital"),
    ("apollo_hosp", 12.9263, 77.5985, "hospital"),
    ("nimhans", 12.9387, 77.5966, "hospital"),
    ("st_johns", 12.9256, 77.6242, "hospital"),
    ("sakra_world", 12.9591, 77.7009, "hospital"),
    ("ms_ramaiah", 12.9930, 77.5585, "hospital"),
]

_EDGE_SPEC: list[tuple[str, str, str, bool]] = [
    ("majestic", "richmond_circle", "primary", False),
    ("richmond_circle", "koramangala", "primary", False),
    ("koramangala", "silk_board", "primary", False),
    ("silk_board", "electronic_city", "trunk", False),
    ("silk_board", "bommanahalli", "secondary", False),
    ("bommanahalli", "hsr_layout", "residential", False),
    ("hsr_layout", "btm_layout", "residential", False),
    ("btm_layout", "jp_nagar", "secondary", False),
    ("jp_nagar", "banashankari", "secondary", False),
    ("banashankari", "jayanagar", "secondary", False),
    ("jayanagar", "apollo_hosp", "secondary", False),
    ("apollo_hosp", "nimhans", "hospital", False),
    ("nimhans", "manipal_hosp", "hospital", False),
    ("manipal_hosp", "st_johns", "hospital", False),
    ("st_johns", "koramangala", "secondary", False),
    ("majestic", "rajajinagar", "primary", False),
    ("rajajinagar", "ms_ramaiah", "secondary", False),
    ("ms_ramaiah", "tumkur_road", "trunk", False),
    ("tumkur_road", "hebbal", "trunk", False),
    ("hebbal", "yelahanka", "primary", False),
    ("majestic", "mg_road", "primary", False),
    ("mg_road", "shivajinagar", "primary", False),
    ("shivajinagar", "ulsoor", "secondary", False),
    ("ulsoor", "indiranagar", "secondary", False),
    ("indiranagar", "domlur", "secondary", False),
    ("domlur", "old_airport_rd", "primary", False),
    ("old_airport_rd", "marathahalli", "primary", False),
    ("marathahalli", "whitefield_hub", "secondary", False),
    ("whitefield_hub", "whitefield", "secondary", False),
    ("whitefield", "varthur", "residential", False),
    ("varthur", "sarjapur", "secondary", False),
    ("hebbal", "nagawara", "secondary", False),
    ("nagawara", "hennur", "residential", False),
    ("hennur", "banaswadi", "residential", False),
    ("banaswadi", "ramamurthy_nagar", "residential", False),
    ("ramamurthy_nagar", "kr_puram", "secondary", False),
    ("kr_puram", "mahadevapura", "secondary", False),
    ("mahadevapura", "whitefield", "secondary", False),
    ("hebbal", "frazer_town", "secondary", False),
    ("frazer_town", "cox_town", "secondary", False),
    ("cox_town", "mg_road", "secondary", False),
    ("majestic", "victoria_hosp", "hospital", False),
    ("koramangala", "manipal_hosp", "hospital", False),
    ("bannerghatta_rd", "fortis_banner", "hospital", False),
    ("jp_nagar", "bannerghatta_rd", "primary", False),
    ("marathahalli", "sakra_world", "hospital", False),
    ("electronic_city", "hosur_road", "trunk", False),
    ("hosur_road", "silk_board", "trunk", False),
    ("indiranagar", "frazer_town", "secondary", False),
    ("shivajinagar", "victoria_hosp", "secondary", False),
    ("bellandur", "marathahalli", "residential", False),
    ("bellandur", "sarjapur", "secondary", False),
    ("koramangala", "bellandur", "secondary", False),
    ("hsr_layout", "bellandur", "residential", False),
]


def _speed(road_type: str) -> float:
    return _SPEED_KMPH.get(road_type, 30.0)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _add_directed_edge(
    nodes: dict[str, RoadNode],
    edges: dict[str, RoadEdge],
    graph: nx.DiGraph,
    src: str,
    tgt: str,
    road_type: str,
    oneway: bool,
) -> None:
    n_src, n_tgt = nodes[src], nodes[tgt]
    length_m = _haversine_m(n_src.lat, n_src.lon, n_tgt.lat, n_tgt.lon)
    speed = _speed(road_type)
    edge_id = f"{src}_{tgt}"
    edge = RoadEdge.from_parts(
        edge_id=edge_id,
        source=src,
        target=tgt,
        length_m=round(length_m, 1),
        road_type=road_type,
        status="OPEN",
        speed_kmh=speed,
        oneway=oneway,
        flood_risk=0.0,
    )
    edges[edge_id] = edge
    graph.add_edge(
        src,
        tgt,
        edge_id=edge_id,
        length_m=edge.length_m,
        road_type=road_type,
        status="OPEN",
        speed_kmh=speed,
        travel_time_s=edge.travel_time_s,
        flood_risk=0.0,
        weight=edge.travel_time_s,
        oneway=oneway,
    )


def build_bundled_graph() -> CityGraph:
    """Build the in-process synthetic Bengaluru Urban sample graph."""
    settings = get_settings()
    nodes: dict[str, RoadNode] = {}
    edges: dict[str, RoadEdge] = {}
    graph = nx.DiGraph()

    for node_id, lat, lon, node_type in _LANDMARK_NODES:
        nodes[node_id] = RoadNode(
            node_id=node_id,
            lat=lat,
            lon=lon,
            node_type=node_type,
            metadata={"synthetic": True, "value_kind": "synthetic"},
        )
        graph.add_node(node_id, lat=lat, lon=lon, node_type=node_type)

    for src, tgt, road_type, oneway in _EDGE_SPEC:
        _add_directed_edge(nodes, edges, graph, src, tgt, road_type, oneway=oneway)
        if not oneway:
            _add_directed_edge(nodes, edges, graph, tgt, src, road_type, oneway=False)

    return CityGraph(
        nodes=nodes,
        edges=edges,
        nx_graph=graph,
        crs=settings.coordinate_system,
        bbox=settings.study_bbox,
        source="BUNDLED_SYNTHETIC",
        retrieved_at=datetime.now(timezone.utc),
        provenance={
            "kind": "synthetic_sample",
            "disclaimer": (
                "Simplified synthetic landmark graph for Bengaluru Urban. "
                "Coordinates are approximate. Not an OSM extract and not for navigation."
            ),
            "excludes": "Bengaluru Rural (including Devanahalli / KIA), BBMP-only city limits",
        },
    )


def city_graph_from_json(payload: dict) -> CityGraph:
    settings = get_settings()
    nodes = {
        n["node_id"]: RoadNode(
            node_id=n["node_id"],
            lat=float(n["lat"]),
            lon=float(n["lon"]),
            node_type=n.get("node_type", "intersection"),
            metadata=n.get("metadata") or {},
        )
        for n in payload["nodes"]
    }
    graph = nx.DiGraph()
    for node in nodes.values():
        graph.add_node(node.node_id, lat=node.lat, lon=node.lon, node_type=node.node_type)

    edges: dict[str, RoadEdge] = {}
    for e in payload["edges"]:
        edge = RoadEdge.from_parts(
            edge_id=e["edge_id"],
            source=e["source"],
            target=e["target"],
            length_m=float(e["length_m"]),
            road_type=e.get("road_type", "unclassified"),
            status=e.get("status", "OPEN"),
            speed_kmh=float(e.get("speed_kmh", 30.0)),
            oneway=bool(e.get("oneway", False)),
            flood_risk=float(e.get("flood_risk", 0.0)),
        )
        edges[edge.edge_id] = edge
        graph.add_edge(
            edge.source,
            edge.target,
            edge_id=edge.edge_id,
            length_m=edge.length_m,
            road_type=edge.road_type,
            status=edge.status,
            speed_kmh=edge.speed_kmh,
            travel_time_s=edge.travel_time_s,
            flood_risk=edge.flood_risk,
            weight=edge.travel_time_s,
            oneway=edge.oneway,
        )

    meta = payload.get("metadata") or {}
    bbox = tuple(meta.get("bbox") or settings.study_bbox)
    return CityGraph(
        nodes=nodes,
        edges=edges,
        nx_graph=graph,
        crs=meta.get("crs", settings.coordinate_system),
        bbox=bbox,  # type: ignore[arg-type]
        source=meta.get("source", "BUNDLED_SYNTHETIC"),
        retrieved_at=datetime.now(timezone.utc),
        provenance=meta.get("provenance") or {},
    )


def city_graph_to_json(graph: CityGraph) -> dict:
    return {
        "metadata": {
            "crs": graph.crs,
            "bbox": list(graph.bbox),
            "source": graph.source,
            "provenance": graph.provenance,
        },
        "nodes": [
            {
                "node_id": n.node_id,
                "lat": n.lat,
                "lon": n.lon,
                "node_type": n.node_type,
                "metadata": n.metadata,
            }
            for n in graph.nodes.values()
        ],
        "edges": [
            {
                "edge_id": e.edge_id,
                "source": e.source,
                "target": e.target,
                "length_m": e.length_m,
                "road_type": e.road_type,
                "status": e.status,
                "speed_kmh": e.speed_kmh,
                "oneway": e.oneway,
                "flood_risk": e.flood_risk,
            }
            for e in graph.edges.values()
        ],
    }


def load_bundled_graph() -> CityGraph:
    """Load the bundled sample graph from disk, generating it if the file is missing."""
    if _SAMPLE_JSON.exists():
        payload = json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))
        graph = city_graph_from_json(payload)
        logger.info(
            "Loaded bundled sample graph from %s (%s nodes, %s edges)",
            _SAMPLE_JSON,
            graph.node_count(),
            graph.edge_count(),
        )
        return graph

    graph = build_bundled_graph()
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _SAMPLE_JSON.write_text(json.dumps(city_graph_to_json(graph), indent=2), encoding="utf-8")
        nx.write_graphml(graph.nx_graph, _SAMPLE_GRAPHML)
    except OSError as exc:
        logger.warning("Could not persist bundled graph files: %s", exc)
    return graph


async def load_osm_graph(
    bbox: tuple[float, float, float, float] | None = None,
    network_type: str | None = None,
) -> CityGraph:
    """
    Download the drive network inside the configured Bengaluru Urban envelope.

    Result is cached on GraphService. Failures fall back to the bundled graph.
    """
    from app.data_sources.osm_source import OSMDataSource

    settings = get_settings()
    source = OSMDataSource()
    result = await source.fetch_graph(
        bbox=bbox or settings.study_bbox,
        network_type=network_type or settings.osm_network_type,
        use_cache=True,
    )
    if result is None:
        logger.warning("OSM download unavailable; using bundled sample graph.")
        return load_bundled_graph()
    return result


class GraphService:
    """Process-lifetime cache for the immutable base road graph."""

    def __init__(self) -> None:
        self._graph: Optional[CityGraph] = None

    @property
    def loaded(self) -> bool:
        return self._graph is not None

    def get(self) -> CityGraph:
        if self._graph is None:
            raise GraphNotLoadedError()
        return self._graph

    def get_copy(self) -> CityGraph:
        return self.get().copy()

    def load_bundled(self) -> CityGraph:
        self._graph = load_bundled_graph()
        return self._graph

    async def load(self) -> CityGraph:
        settings = get_settings()
        if settings.use_bundled_graph:
            return self.load_bundled()
        try:
            self._graph = await load_osm_graph()
        except Exception as exc:  # noqa: BLE001
            logger.warning("OSM load failed (%s); falling back to bundled graph", exc)
            return self.load_bundled()
        return self._graph


graph_service = GraphService()
