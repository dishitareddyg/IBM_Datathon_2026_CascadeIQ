"""Service singletons."""

from app.services.city_service import city_service
from app.services.graph_service import build_bundled_graph, graph_service, load_osm_graph
from app.services.risk_service import risk_service
from app.services.routing_service import routing_service
from app.services.cascade_service import cascade_service
from app.services.intervention_service import intervention_service
from app.services.simulation_service import simulation_service
from app.services.evaluation_service import evaluation_service
from app.services.weather_service import weather_service

__all__ = [
    "city_service",
    "graph_service",
    "build_bundled_graph",
    "load_osm_graph",
    "risk_service",
    "routing_service",
    "cascade_service",
    "intervention_service",
    "simulation_service",
    "evaluation_service",
    "weather_service",
]
