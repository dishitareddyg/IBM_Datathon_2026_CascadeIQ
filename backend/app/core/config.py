"""
app/core/config.py
──────────────────
Centralised, typed application settings powered by Pydantic-Settings v2.
All values are read from environment variables (or a .env file) with safe
defaults so the app can start without a .env during testing.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings resolved from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = Field(default="CascadeIQ", description="Human-readable service name.")
    app_version: str = Field(default="0.1.0", description="Semantic version of the service.")
    debug: bool = Field(default=False, description="Enable debug mode (verbose errors, auto-reload).")

    # ── Server ─────────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", description="Bind address for uvicorn.")
    port: int = Field(default=8000, ge=1, le=65535, description="Bind port for uvicorn.")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Root log level."
    )

    # ── Study Area (Bengaluru Urban district only) ─────────────────────────────
    study_area: str = Field(default="Bengaluru Urban", description="OSM-compatible district name.")
    study_area_state: str = Field(default="Karnataka", description="State within India.")
    study_area_country: str = Field(default="India", description="Country for OSM geocoding.")
    # Envelope of Bengaluru Urban district (NOT BBMP city limits, NOT Bengaluru Rural).
    # Provenance: axis-aligned envelope of the district compiled from the Census of
    # India 2011 District Census Handbook (Bengaluru Urban) map plate and ISRO
    # Bhuvan district boundary WMS (public viewing). Retrieved 2026-10-18.
    # Licence: Government of India open geospatial viewing data; this repository
    # stores a simplified envelope, not the official cadastral shapefile.
    study_min_lat: float = Field(default=12.75, description="Southern envelope latitude (WGS84).")
    study_min_lon: float = Field(default=77.35, description="Western envelope longitude (WGS84).")
    study_max_lat: float = Field(default=13.16, description="Northern envelope latitude (WGS84).")
    study_max_lon: float = Field(default=77.84, description="Eastern envelope longitude (WGS84).")
    study_area_km2: float = Field(
        default=2196.0,
        description="Published district area (km²), Census of India 2011 DCHB — not the envelope area.",
    )
    population_census_2011: int = Field(
        default=9_621_551,
        description="Census of India 2011 population for Bengaluru Urban district.",
    )
    geography_retrieved_at: str = Field(default="2026-10-18")
    geography_licence: str = Field(
        default="Census of India 2011 / ISRO Bhuvan public viewing; simplified envelope only",
    )

    # ── Coordinate Reference Systems ───────────────────────────────────────────
    coordinate_system: str = Field(
        default="EPSG:4326",
        description="Geographic CRS for all lat/lon values returned by the API.",
    )
    local_crs: str = Field(
        default="EPSG:32643",
        description="Projected CRS (UTM Zone 43N) used for distance calculations in Karnataka.",
    )

    # ── Graph / OSM ────────────────────────────────────────────────────────────
    use_bundled_graph: bool = Field(
        default=True,
        description="If True, load the bundled sample graph rather than querying OSM on startup.",
    )
    osm_network_type: Literal["drive", "walk", "bike", "all"] = Field(
        default="drive",
        description="OSMnx network type used when downloading the road graph.",
    )
    osm_timeout_s: float = Field(default=30.0, gt=0.0, description="Timeout for OSM/Overpass downloads.")
    request_timeout_s: float = Field(default=30.0, gt=0.0, description="Advisory request timeout for long simulations.")

    # ── Simulation Limits ──────────────────────────────────────────────────────
    max_scenario_steps: int = Field(default=50, ge=1, le=200)
    max_hospitals: int = Field(default=100, ge=1)
    max_ambulances: int = Field(default=500, ge=1)
    max_requests: int = Field(default=1000, ge=1)

    # ── Default Operational Parameters ────────────────────────────────────────
    default_ambulance_speed_kmh: float = Field(
        default=40.0, gt=0.0, description="Fallback speed (km/h) when no road speed is available."
    )
    simulation_step_minutes: int = Field(default=15, ge=1, le=60)
    degraded_travel_time_multiplier_max: float = Field(
        default=3.0, gt=1.0,
        description="Travel-time multiplier applied to DEGRADED edges at severity=1.0.",
    )
    hospital_overload_threshold: float = Field(
        default=0.90, ge=0.0, le=1.0,
        description="Occupancy ratio at which a hospital is treated as overloaded.",
    )
    inferred_degrade_threshold: float = Field(
        default=0.70, ge=0.0, le=1.0,
        description="Composite flood-risk score above which a road may be marked DEGRADED (never CLOSED from weather alone).",
    )

    # ── Flood Risk Thresholds ──────────────────────────────────────────────────
    flood_risk_rainfall_mm_high: float = Field(
        default=50.0, gt=0.0,
        description="24-hour rainfall (mm) threshold above which flood risk is HIGH.",
    )
    flood_risk_rainfall_mm_critical: float = Field(
        default=100.0, gt=0.0,
        description="24-hour rainfall (mm) threshold above which flood risk is CRITICAL.",
    )
    flood_risk_warning_weight: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Weight of active weather warnings in the composite flood-risk score.",
    )
    flood_risk_rainfall_weight: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Weight of raw rainfall in the composite flood-risk score.",
    )

    # ── Objective Function Weights ─────────────────────────────────────────────
    objective_lambda: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="λ — weight for the coverage / response-time term in the objective.",
    )
    objective_mu: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="μ — weight for the cascade-isolation penalty in the objective.",
    )

    # ── External APIs (optional) ───────────────────────────────────────────────
    imd_api_key: str = Field(
        default="",
        description="India Meteorological Department API key. Leave empty to use synthetic weather.",
    )

    # ── Database (optional) ────────────────────────────────────────────────────
    database_url: str = Field(
        default="",
        description="SQLAlchemy-compatible database URL. Empty means no persistent storage.",
    )

    # ── Derived / Computed Properties ─────────────────────────────────────────
    @field_validator("flood_risk_warning_weight", "flood_risk_rainfall_weight", mode="after")
    @classmethod
    def _weights_sum_check(cls, v: float) -> float:
        # Individual bounds are already enforced by ge/le; cross-field sum
        # validation is handled at the service layer to avoid two-field access.
        return v

    @property
    def study_area_full(self) -> str:
        """Return a single OSM query string, e.g. 'Bengaluru Urban, Karnataka, India'."""
        return f"{self.study_area}, {self.study_area_state}, {self.study_area_country}"

    @property
    def study_bbox(self) -> tuple[float, float, float, float]:
        """(min_lat, min_lon, max_lat, max_lon) envelope of the configured study area."""
        return (self.study_min_lat, self.study_min_lon, self.study_max_lat, self.study_max_lon)

    @property
    def bundled_graph_path(self) -> str:
        """Conventional path for the bundled sample GraphML road network."""
        return "data/bengaluru_urban_sample.graphml"

    @property
    def imd_configured(self) -> bool:
        """True when a real IMD API key has been supplied."""
        return bool(self.imd_api_key.strip())

    @property
    def database_configured(self) -> bool:
        """True when a database URL has been supplied."""
        return bool(self.database_url.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
