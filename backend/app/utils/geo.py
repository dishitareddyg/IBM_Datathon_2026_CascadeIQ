"""
Geospatial utility functions for CascadeIQ.

All functions operate on WGS 84 (EPSG:4326) coordinates unless explicitly
stated otherwise.  Distance calculations use the Haversine formula for speed;
for high-precision metric calculations, use :func:`project_point` to convert
to UTM Zone 43 N (EPSG:32643) first.

Study area
----------
Bengaluru Urban district, Karnataka, India.
  Approximate bounding box : (12.75, 77.35, 13.18, 77.85)
  Centre                   : 13.0°N  77.6°E
  Area                     : ~741 km²
  Storage CRS              : EPSG:4326 (WGS 84)
  Distance CRS             : EPSG:32643 (UTM Zone 43 N)
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# Earth's mean radius in metres (WGS 84 authalic sphere approximation)
_EARTH_RADIUS_M: float = 6_371_008.8

# Known district bounding boxes.
# Source: approximate bounds from Survey of India / Bhuvan portal
#         cross-referenced with Census of India 2011 district maps.
# Format: (min_lat, min_lon, max_lat, max_lon) in WGS 84.
_DISTRICT_BBOXES: dict[tuple[str, str], tuple[float, float, float, float]] = {
    ("bengaluru urban", "karnataka"): (12.75, 77.35, 13.18, 77.85),
    ("bangalore urban", "karnataka"): (12.75, 77.35, 13.18, 77.85),
    ("bengaluru rural", "karnataka"): (12.90, 77.00, 13.30, 77.55),
    ("mysuru", "karnataka"): (12.10, 76.40, 12.60, 76.80),
}


# ---------------------------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------------------------

def validate_coordinate(lat: float, lon: float, bbox: tuple) -> bool:
    """
    Check whether a coordinate falls within the study area bounding box.

    Parameters
    ----------
    lat, lon:
        WGS 84 latitude and longitude in decimal degrees.
    bbox:
        ``(min_lat, min_lon, max_lat, max_lon)`` defining the study area.

    Returns
    -------
    bool
        ``True`` when the coordinate is strictly within (or on the boundary
        of) the bbox.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must be (min_lat, min_lon, max_lat, max_lon); got {bbox!r}")
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance in metres between two WGS 84 points.

    Uses the Haversine formula.  Accurate to within ~0.5 % for distances
    under 1 000 km (well within the Bengaluru Urban study area).

    Parameters
    ----------
    lat1, lon1:
        Origin point (decimal degrees).
    lat2, lon2:
        Destination point (decimal degrees).

    Returns
    -------
    float
        Distance in metres.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(a))
    return _EARTH_RADIUS_M * c


# ---------------------------------------------------------------------------
# Graph snapping
# ---------------------------------------------------------------------------

def snap_to_nearest_node(
    lat: float,
    lon: float,
    nx_graph,               # networkx.DiGraph
    node_coords: Optional[dict[str, tuple[float, float]]] = None,
) -> Optional[str]:
    """
    Find the nearest road-graph node to a WGS 84 coordinate.

    The search uses Haversine distance to all nodes and returns the closest.
    This is O(N) in the number of nodes; for very large graphs consider a
    spatial index (e.g., ``scipy.spatial.cKDTree``).

    Parameters
    ----------
    lat, lon:
        Query coordinate in WGS 84.
    nx_graph:
        A ``networkx.DiGraph`` where each node has ``lat`` and ``lon``
        attributes (as set by :mod:`app.data_sources.osm_source`).
    node_coords:
        Optional pre-built mapping ``{node_id: (lat, lon)}`` for speed when
        snap_to_nearest_node is called many times for the same graph.

    Returns
    -------
    str or None
        The ``node_id`` of the nearest node, or ``None`` if the graph is empty.
    """
    if nx_graph is None or len(nx_graph.nodes) == 0:
        logger.warning("snap_to_nearest_node: graph is empty, cannot snap.")
        return None

    best_node: Optional[str] = None
    best_dist: float = math.inf

    for node_id, data in nx_graph.nodes(data=True):
        n_lat = data.get("lat") or data.get("y")
        n_lon = data.get("lon") or data.get("x")
        if n_lat is None or n_lon is None:
            if node_coords and str(node_id) in node_coords:
                n_lat, n_lon = node_coords[str(node_id)]
            else:
                continue
        dist = haversine_distance(lat, lon, float(n_lat), float(n_lon))
        if dist < best_dist:
            best_dist = dist
            best_node = str(node_id)

    if best_node is None:
        logger.warning(
            "snap_to_nearest_node: no valid node found for (%.5f, %.5f).", lat, lon
        )
    return best_node


# ---------------------------------------------------------------------------
# CRS projection
# ---------------------------------------------------------------------------

def project_point(
    lat: float,
    lon: float,
    source_crs: str = "EPSG:4326",
    target_crs: str = "EPSG:32643",
) -> tuple[float, float]:
    """
    Project a geographic point from *source_crs* to *target_crs*.

    Uses PyProj for accurate datum-aware transformation.

    Parameters
    ----------
    lat, lon:
        Input coordinates.  For EPSG:4326 these are decimal degrees; for
        projected CRS they are easting/northing metres.
    source_crs, target_crs:
        EPSG authority strings (e.g. ``'EPSG:4326'``, ``'EPSG:32643'``).

    Returns
    -------
    tuple[float, float]
        ``(x, y)`` in the target CRS units.  For UTM projections this is
        ``(easting_m, northing_m)``.

    Raises
    ------
    ImportError
        If PyProj is not installed.
    pyproj.exceptions.CRSError
        If an invalid CRS string is supplied.
    """
    from pyproj import Transformer  # noqa: PLC0415
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    # PyProj with always_xy=True takes (longitude, latitude)
    x, y = transformer.transform(lon, lat)
    return float(x), float(y)


# ---------------------------------------------------------------------------
# Bounding box helpers
# ---------------------------------------------------------------------------

def validate_crs(storage_crs: str, distance_crs: str) -> None:
    """Reject distance work unless storage is geographic and local CRS is projected UTM 43N."""
    if storage_crs.upper() != "EPSG:4326":
        raise ValueError(f"Storage CRS must be EPSG:4326 (WGS84); got {storage_crs}")
    if distance_crs.upper() != "EPSG:32643":
        raise ValueError(
            f"Distance CRS for Karnataka must be EPSG:32643 (UTM Zone 43N); got {distance_crs}"
        )


def projected_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    source_crs: str = "EPSG:4326",
    target_crs: str = "EPSG:32643",
) -> float:
    """Euclidean distance in metres after projecting both points."""
    x1, y1 = project_point(lat1, lon1, source_crs, target_crs)
    x2, y2 = project_point(lat2, lon2, source_crs, target_crs)
    return math.hypot(x2 - x1, y2 - y1)


def district_polygon(bbox: tuple):
    """Axis-aligned envelope polygon for the configured district bbox (not cadastral)."""
    from shapely.geometry import box

    min_lat, min_lon, max_lat, max_lon = bbox
    return box(min_lon, min_lat, max_lon, max_lat)


def bbox_area_km2(bbox: tuple) -> float:
    """
    Approximate area of an axis-aligned bounding box in km².

    Uses the Haversine formula to compute the width and height of the box.
    Accurate to within ~1 % for boxes of typical district size.

    Parameters
    ----------
    bbox:
        ``(min_lat, min_lon, max_lat, max_lon)`` in WGS 84.

    Returns
    -------
    float
        Area in km².
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    # Width: distance along bottom edge (constant latitude)
    width_m = haversine_distance(min_lat, min_lon, min_lat, max_lon)
    # Height: distance along left edge (constant longitude)
    height_m = haversine_distance(min_lat, min_lon, max_lat, min_lon)
    area_m2 = width_m * height_m
    return area_m2 / 1_000_000.0


def generate_bbox_for_district(district: str, state: str) -> tuple:
    """
    Return the known bounding box for a district / state combination.

    Bounding boxes are hardcoded from Survey of India / Bhuvan portal data.
    The lookup is case-insensitive.

    Currently supported:
      * Bengaluru Urban, Karnataka → ``(12.75, 77.35, 13.18, 77.85)``
      * Bengaluru Rural, Karnataka → ``(12.90, 77.00, 13.30, 77.55)``
      * Mysuru, Karnataka          → ``(12.10, 76.40, 12.60, 76.80)``

    Parameters
    ----------
    district, state:
        Case-insensitive district and state names.

    Returns
    -------
    tuple
        ``(min_lat, min_lon, max_lat, max_lon)`` in WGS 84.

    Raises
    ------
    ValueError
        If the district is not in the known catalogue.

    Note
    ----
    Source: approximate bounds from Survey of India / Bhuvan portal
    (https://bhuvan.nrsc.gov.in), cross-referenced with Census of India 2011
    district boundary maps.
    """
    key = (district.strip().lower(), state.strip().lower())
    if key in _DISTRICT_BBOXES:
        return _DISTRICT_BBOXES[key]

    # Fuzzy fallback: match district name alone
    for (d, s), bbox in _DISTRICT_BBOXES.items():
        if d == key[0]:
            logger.warning(
                "generate_bbox_for_district: state '%s' not matched; "
                "using bbox for '%s, %s'.", state, d, s
            )
            return bbox

    raise ValueError(
        f"No known bounding box for district='{district}', state='{state}'. "
        f"Available: {[f'{d}, {s}' for d, s in _DISTRICT_BBOXES]}"
    )
