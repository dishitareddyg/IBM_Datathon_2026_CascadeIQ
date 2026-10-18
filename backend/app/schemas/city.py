"""
app/schemas/city.py
────────────────────
Pydantic v2 schemas for the city road-network graph API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BoundingBox


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


# ── Graph Node ─────────────────────────────────────────────────────────────────
class NodeSchema(_Base):
    """
    A single node in the city road-network graph.

    ``node_type`` classifies whether the node is a plain road intersection,
    a mapped hospital entrance, or another critical facility (e.g., fire station).
    """

    node_id: str = Field(..., description="OSM node ID (string-cast integer).")
    lat: float = Field(..., description="Latitude of the node centroid (WGS-84).")
    lon: float = Field(..., description="Longitude of the node centroid (WGS-84).")
    node_type: Literal["intersection", "hospital", "facility"] = Field(
        default="intersection",
        description="Semantic classification of the node.",
    )


# ── Graph Edge ─────────────────────────────────────────────────────────────────
class EdgeSchema(_Base):
    """
    A directed road-network edge connecting two nodes.

    ``status`` reflects the current operational state of the road segment
    after flood-driven disruptions have been applied.
    ``travel_time_s`` is pre-computed from ``length_m`` and ``speed_kmh``
    and accounts for any degradation factor.
    """

    edge_id: str = Field(
        ...,
        description="Composite identifier '{source_node}-{target_node}' (unique per direction).",
    )
    source_node: str = Field(..., description="OSM ID of the origin node.")
    target_node: str = Field(..., description="OSM ID of the destination node.")
    length_m: float = Field(..., ge=0.0, description="Geometric length of the edge in metres.")
    road_type: str = Field(
        default="unclassified",
        description="OSM highway tag value (e.g., 'primary', 'residential').",
    )
    status: Literal["OPEN", "DEGRADED", "CLOSED"] = Field(
        default="OPEN",
        description="Operational status after applying flood disruptions.",
    )
    speed_kmh: float = Field(
        ..., gt=0.0,
        description="Effective vehicle speed in km/h (reduced when DEGRADED).",
    )
    travel_time_s: float = Field(
        ..., ge=0.0,
        description="Pre-computed travel time in seconds (length_m / effective_speed).",
    )
    oneway: bool = Field(
        default=False,
        description="True if the road is legally one-directional.",
    )
    flood_risk: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Inferred flood-related disruption score [0, 1]. Not an observed water depth.",
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Confidence of the current disruption estimate, if any.",
    )


# ── Graph Metadata ─────────────────────────────────────────────────────────────
class GraphMetadataSchema(_Base):
    """
    Summary statistics and provenance for the loaded road-network graph.
    """

    node_count: int = Field(..., ge=0, description="Total number of nodes in the graph.")
    edge_count: int = Field(..., ge=0, description="Total number of directed edges.")
    bbox: BoundingBox = Field(..., description="Bounding box of the graph extent.")
    crs: str = Field(
        default="EPSG:4326",
        description="Coordinate Reference System of node lat/lon values.",
    )
    source: str = Field(
        default="OpenStreetMap",
        description="Data provenance label.",
    )
    retrieved_at: datetime = Field(
        ...,
        description="UTC timestamp at which the graph was downloaded or last updated.",
    )
    network_type: str = Field(
        default="drive",
        description="OSMnx network type used during graph construction.",
    )


# ── Full Graph Response ────────────────────────────────────────────────────────
class CityGraphResponse(_Base):
    """
    Complete serialised road-network graph returned by GET /api/v1/city/graph.

    For large districts this may be several MB; callers should consider
    requesting only the metadata endpoint for lightweight status checks.
    """

    metadata: GraphMetadataSchema
    nodes: list[NodeSchema] = Field(default_factory=list)
    edges: list[EdgeSchema] = Field(default_factory=list)


# ── City Metadata Response ─────────────────────────────────────────────────────
class CityMetadataResponse(_Base):
    """
    High-level descriptive metadata about the study area.
    Returned by GET /api/v1/city/metadata.
    """

    district: str = Field(..., description="Administrative district name.")
    state: str = Field(..., description="State name.")
    country: str = Field(..., description="Country name.")
    area_km2: float = Field(..., ge=0.0, description="Approximate area of the district in km².")
    bbox: BoundingBox = Field(..., description="Geographic bounding box.")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System.")
    population_approx: int = Field(
        ..., ge=0,
        description="Approximate population (latest census / public estimate).",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="List of data-source labels (e.g., 'OpenStreetMap', 'IMD', 'Synthetic').",
    )
    boundary_provenance: str = Field(
        default="",
        description="Provenance, licence and retrieval date of the district envelope.",
    )
    boundary_note: str = Field(
        default=(
            "Study area is Bengaluru Urban district. This is not BBMP city limits, "
            "not Bengaluru Rural, and not the full metropolitan region."
        ),
    )
