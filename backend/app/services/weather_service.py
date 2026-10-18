"""Weather retrieval with synthetic default and optional IMD attempt."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.data_sources.imd_source import IMDDataSource
from app.data_sources.synthetic_source import SyntheticDataSource
from app.repositories.weather_repository import weather_repo
from app.schemas.common import BoundingBox
from app.schemas.weather import RainfallObservation, WeatherSource, WeatherStatus, WeatherWarning

_ALERT_TO_SEVERITY = {
    "GREEN_ALERT": "WATCH",
    "YELLOW_ALERT": "WARNING",
    "ORANGE_ALERT": "SEVERE",
    "RED_ALERT": "EXTREME",
    "WATCH": "WATCH",
    "WARNING": "WARNING",
    "SEVERE": "SEVERE",
    "EXTREME": "EXTREME",
}


class WeatherService:
    def __init__(self) -> None:
        self._synthetic = SyntheticDataSource()
        self._imd = IMDDataSource()

    async def _refresh(self, seed: int = 42) -> None:
        settings = get_settings()
        bbox = settings.study_bbox
        observations: list[dict] = []
        warnings: list[dict] = []
        source_tag = "SYNTHETIC"

        if settings.imd_configured:
            try:
                observations = await self._imd.fetch_rainfall(bbox)
                warnings = await self._imd.fetch_warnings(settings.study_area)
                source_tag = "IMD" if self._imd.is_available else "IMD_FALLBACK"
            except Exception:
                observations, warnings = [], []

        if not observations:
            bundle = self._synthetic.generate_scenario("HEAVY", seed, bbox=bbox)
            observations = bundle["observations"]
            warnings = bundle["warnings"]
            source_tag = "SYNTHETIC"

        weather_repo.update(observations, warnings)
        weather_repo.source_tag = source_tag  # type: ignore[attr-defined]

    async def observations(self, seed: int = 42) -> list[RainfallObservation]:
        if not weather_repo.is_fresh():
            await self._refresh(seed)
        items: list[RainfallObservation] = []
        for raw in weather_repo.get_observations():
            mm1 = float(raw.get("rainfall_mm_1h", raw.get("rainfall_mm_hr", 0.0)))
            mm24 = float(raw.get("rainfall_mm_24h", mm1 * 10.0))
            source_raw = str(raw.get("source", "SYNTHETIC")).upper()
            source = WeatherSource.SYNTHETIC
            if source_raw.startswith("IMD"):
                source = WeatherSource.IMD
            elif source_raw == "HISTORICAL":
                source = WeatherSource.HISTORICAL
            observed = raw.get("observed_at")
            if isinstance(observed, str):
                observed_at = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            else:
                observed_at = datetime.now(timezone.utc)
            items.append(
                RainfallObservation(
                    station_id=str(raw.get("station_id", "unknown")),
                    lat=float(raw["lat"]),
                    lon=float(raw["lon"]),
                    rainfall_mm_1h=round(mm1, 2),
                    rainfall_mm_24h=round(mm24, 2),
                    observed_at=observed_at,
                    source=source,
                )
            )
        return items

    async def warnings(self, seed: int = 42) -> list[WeatherWarning]:
        if not weather_repo.is_fresh():
            await self._refresh(seed)
        settings = get_settings()
        min_lat, min_lon, max_lat, max_lon = settings.study_bbox
        items: list[WeatherWarning] = []
        for raw in weather_repo.get_warnings():
            issued = raw.get("issued_at")
            until = raw.get("valid_until")
            if isinstance(issued, str):
                issued_at = datetime.fromisoformat(issued.replace("Z", "+00:00"))
            else:
                issued_at = datetime.now(timezone.utc)
            if isinstance(until, str):
                valid_until = datetime.fromisoformat(until.replace("Z", "+00:00"))
            else:
                valid_until = issued_at
            if valid_until <= issued_at:
                continue
            source_raw = str(raw.get("source", "SYNTHETIC")).upper()
            source = WeatherSource.SYNTHETIC
            if source_raw.startswith("IMD"):
                source = WeatherSource.IMD
            wtype = str(raw.get("warning_type", "HEAVY_RAIN"))
            severity = _ALERT_TO_SEVERITY.get(wtype, raw.get("severity", "WARNING"))
            if isinstance(severity, float):
                severity = "SEVERE" if severity >= 0.7 else "WARNING"
            items.append(
                WeatherWarning(
                    warning_id=str(raw.get("warning_id", "warn")),
                    warning_type="HEAVY_RAIN" if "ALERT" in wtype else wtype,
                    severity=severity,  # type: ignore[arg-type]
                    description=str(raw.get("description", "")),
                    issued_at=issued_at,
                    valid_until=valid_until,
                    affected_area=BoundingBox(
                        min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon
                    ),
                    source=source,
                )
            )
        return items

    async def status(self, seed: int = 42) -> WeatherStatus:
        observations = await self.observations(seed)
        warnings = await self.warnings(seed)
        freshness = max((o.observed_at for o in observations), default=datetime.now(timezone.utc))
        return WeatherStatus(
            current_observations=observations,
            active_warnings=warnings,
            data_freshness=freshness,
            disclaimer=(
                "Weather values are SYNTHETIC or fallback estimates for a student simulator. "
                "They are not IMD observations of rainfall on specific roads and must not be "
                "treated as flood-depth measurements."
            ),
        )


weather_service = WeatherService()
