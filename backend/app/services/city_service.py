"""City metadata and compact graph serialisation for map clients."""

from __future__ import annotations

from app.core.config import get_settings
from app.models.graph import CityGraph
from app.schemas.city import (
    CityGraphResponse,
    CityMetadataResponse,
    EdgeSchema,
    GraphMetadataSchema,
    NodeSchema,
)
from app.schemas.common import BoundingBox
from app.services.graph_service import graph_service
from app.utils.geo import bbox_area_km2, district_polygon, validate_crs


class CityService:
    def metadata(self) -> CityMetadataResponse:
        settings = get_settings()
        validate_crs(settings.coordinate_system, settings.local_crs)
        min_lat, min_lon, max_lat, max_lon = settings.study_bbox
        polygon = district_polygon(settings.study_bbox)
        envelope_km2 = bbox_area_km2(settings.study_bbox)
        return CityMetadataResponse(
            district=settings.study_area,
            state=settings.study_area_state,
            country=settings.study_area_country,
            area_km2=settings.study_area_km2,
            bbox=BoundingBox(
                min_lat=min_lat,
                min_lon=min_lon,
                max_lat=max_lat,
                max_lon=max_lon,
            ),
            crs=settings.coordinate_system,
            population_approx=settings.population_census_2011,
            data_sources=[
                "OpenStreetMap (ODbL 1.0) — optional live roads",
                "Bundled synthetic sample graph",
                "Census of India 2011 District Census Handbook (Bengaluru Urban)",
                "ISRO Bhuvan district envelope (viewing, 2026-10-18)",
                "Synthetic weather (IMD live API optional)",
            ],
            boundary_provenance=(
                f"Envelope of Bengaluru Urban district compiled from Census of India 2011 "
                f"DCHB map plate and ISRO Bhuvan district WMS. Retrieved {settings.geography_retrieved_at}. "
                f"Licence: {settings.geography_licence}. Envelope area ≈ {envelope_km2:.0f} km²; "
                f"published district area {settings.study_area_km2:.0f} km². "
                f"Polygon vertex count={len(polygon.exterior.coords)}."
            ),
            boundary_note=(
                "Study area is Bengaluru Urban district, Karnataka. "
                "It is not BBMP city limits (~741 km²), not Bengaluru Rural, "
                "and not the Bengaluru Metropolitan Region. "
                "Kempegowda International Airport (Devanahalli) is outside this study area."
            ),
        )

    def compact_graph(self, graph: CityGraph | None = None) -> CityGraphResponse:
        settings = get_settings()
        city = graph or graph_service.get()
        min_lat, min_lon, max_lat, max_lon = city.bbox
        nodes = [
            NodeSchema(
                node_id=n.node_id,
                lat=n.lat,
                lon=n.lon,
                node_type=n.node_type if n.node_type in ("intersection", "hospital", "facility") else "intersection",
            )
            for n in city.nodes.values()
        ]
        edges = [
            EdgeSchema(
                edge_id=e.edge_id,
                source_node=e.source,
                target_node=e.target,
                length_m=e.length_m,
                road_type=e.road_type,
                status=e.status if e.status in ("OPEN", "DEGRADED", "CLOSED") else "OPEN",
                speed_kmh=e.speed_kmh,
                travel_time_s=round(e.travel_time_s, 2),
                oneway=e.oneway,
                flood_risk=round(e.flood_risk, 3),
                confidence=e.metadata.get("confidence") if e.metadata else None,
            )
            for e in city.edges.values()
        ]
        metadata = GraphMetadataSchema(
            node_count=len(nodes),
            edge_count=len(edges),
            bbox=BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon),
            crs=city.crs or settings.coordinate_system,
            source=city.source,
            retrieved_at=city.retrieved_at,
            network_type=settings.osm_network_type,
        )
        return CityGraphResponse(metadata=metadata, nodes=nodes, edges=edges)


city_service = CityService()
