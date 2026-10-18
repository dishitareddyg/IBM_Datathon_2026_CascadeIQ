"""
Fully synthetic data source for offline / testing operation.

This module generates statistically plausible rainfall observations and weather
warnings for Bengaluru Urban district **without** requiring any external API.
All data are computer-generated using numpy; they carry a mandatory disclaimer
and a ``source='SYNTHETIC'`` tag.

Severity levels
---------------
``LIGHT``    :  0 –  15 mm/hr
``MODERATE`` : 15 –  40 mm/hr
``HEAVY``    : 40 –  80 mm/hr
``EXTREME``  : 80 – 150 mm/hr
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import numpy as np

from app.data_sources.base import DataSource

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------

class RainfallSeverity(str, Enum):
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    EXTREME = "EXTREME"


# Rainfall range per severity level (mm/hr)
_SEVERITY_RANGE: dict[RainfallSeverity, tuple[float, float]] = {
    RainfallSeverity.LIGHT: (0.0, 15.0),
    RainfallSeverity.MODERATE: (15.0, 40.0),
    RainfallSeverity.HEAVY: (40.0, 80.0),
    RainfallSeverity.EXTREME: (80.0, 150.0),
}

# Warning type & severity mapping
_SEVERITY_WARNING: dict[RainfallSeverity, tuple[str, float]] = {
    RainfallSeverity.LIGHT: ("GREEN_ALERT", 0.2),
    RainfallSeverity.MODERATE: ("YELLOW_ALERT", 0.45),
    RainfallSeverity.HEAVY: ("ORANGE_ALERT", 0.70),
    RainfallSeverity.EXTREME: ("RED_ALERT", 0.95),
}

_DISCLAIMER = (
    "DISCLAIMER: This observation is entirely SYNTHETIC and computer-generated. "
    "It does NOT represent real meteorological data and must NOT be used for "
    "operational weather forecasting or emergency decision-making outside of "
    "controlled simulation contexts."
)


class SyntheticDataSource(DataSource):
    """
    Synthetic weather data source for Bengaluru Urban district.

    Station coordinates are hardcoded class constants.  Provenance note:
    coordinates are approximate centroids of named Bengaluru localities,
    cross-referenced against OpenStreetMap and Google Maps (accessed 2024-09).
    They are **not** official IMD automatic weather station (AWS) locations.
    """

    # ------------------------------------------------------------------
    # Station catalogue  (name, lat, lon)
    # NOTE: Approximate locality centroids — NOT official IMD AWS locations.
    # Source: OpenStreetMap nominatim + Google Maps cross-reference, 2024-09.
    # ------------------------------------------------------------------
    STATIONS: list[tuple[str, float, float]] = [
        ("Majestic",       12.9767, 77.5713),
        ("Whitefield",     12.9698, 77.7500),
        ("Electronic City", 12.8445, 77.6602),
        ("Yeshwanthpur",   13.0275, 77.5439),
        ("Hebbal",         13.0358, 77.5970),
        ("Koramangala",    12.9352, 77.6245),
        ("Marathahalli",   12.9560, 77.7010),
        ("Yelahanka",      13.1007, 77.5963),
    ]

    # ------------------------------------------------------------------

    def __init__(self, default_seed: int = 42, default_severity: RainfallSeverity = RainfallSeverity.HEAVY):
        self._default_seed = default_seed
        self._default_severity = default_severity

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    @property
    def source_name(self) -> str:
        return "SYNTHETIC"

    @property
    def is_available(self) -> bool:
        # Synthetic source is always available — no external dependency.
        return True

    async def fetch_rainfall(self, bbox: tuple) -> list[dict]:
        """
        Generate synthetic rainfall observations for stations within *bbox*.

        Uses the default seed and severity set at construction time.  For
        deterministic generation with a specific seed/severity, call
        :meth:`generate_scenario` directly.
        """
        return self.generate_scenario(
            severity=self._default_severity.value,
            seed=self._default_seed,
            bbox=bbox,
        )["observations"]

    async def fetch_warnings(self, district: str) -> list[dict]:
        """Generate 1–3 synthetic weather warnings for *district*."""
        return self.generate_scenario(
            severity=self._default_severity.value,
            seed=self._default_seed,
        )["warnings"]

    # ------------------------------------------------------------------
    # Deterministic generation
    # ------------------------------------------------------------------

    def generate_scenario(
        self,
        severity: str,
        seed: int,
        bbox: Optional[tuple] = None,
    ) -> dict:
        """
        Generate a complete synthetic weather scenario deterministically.

        Parameters
        ----------
        severity:
            One of ``'LIGHT'``, ``'MODERATE'``, ``'HEAVY'``, ``'EXTREME'``.
        seed:
            Random seed for full reproducibility.
        bbox:
            Optional ``(min_lat, min_lon, max_lat, max_lon)`` filter.
            When provided, only stations within the bbox are included.

        Returns
        -------
        dict
            ``{"observations": [...], "warnings": [...]}`` — both lists
            contain dicts matching the API schema.
        """
        try:
            sev = RainfallSeverity(severity.upper())
        except ValueError:
            logger.warning("Unknown severity '%s'; defaulting to HEAVY.", severity)
            sev = RainfallSeverity.HEAVY

        rng = np.random.default_rng(seed)
        now_utc = datetime.now(timezone.utc)
        rain_min, rain_max = _SEVERITY_RANGE[sev]

        # ----------------------------------------------------------
        # Filter stations by bbox if supplied
        # ----------------------------------------------------------
        stations = self.STATIONS
        if bbox is not None:
            min_lat, min_lon, max_lat, max_lon = bbox
            stations = [
                s for s in stations
                if min_lat <= s[1] <= max_lat and min_lon <= s[2] <= max_lon
            ]
        if not stations:
            stations = self.STATIONS   # fall back to full set if bbox too narrow

        # ----------------------------------------------------------
        # Observations
        # ----------------------------------------------------------
        observations: list[dict] = []
        for idx, (name, lat, lon) in enumerate(stations):
            # Add a small per-station spatial perturbation so neighbouring
            # stations have correlated but distinct values.
            base_rain = float(rng.uniform(rain_min, rain_max))
            jitter = float(rng.normal(0, (rain_max - rain_min) * 0.05))
            rainfall = max(0.0, min(150.0, base_rain + jitter))

            obs_time = now_utc - timedelta(minutes=int(rng.integers(0, 30)))
            observations.append({
                "station_id": f"SYN_{idx:03d}",
                "station_name": name,
                "lat": lat,
                "lon": lon,
                "rainfall_mm_hr": round(rainfall, 2),
                "observed_at": obs_time.isoformat(),
                "source": "SYNTHETIC",
                "disclaimer": _DISCLAIMER,
            })

        # ----------------------------------------------------------
        # Warnings  (1–3 depending on severity)
        # ----------------------------------------------------------
        warning_type, base_severity = _SEVERITY_WARNING[sev]
        n_warnings = {
            RainfallSeverity.LIGHT: 1,
            RainfallSeverity.MODERATE: 1,
            RainfallSeverity.HEAVY: 2,
            RainfallSeverity.EXTREME: 3,
        }[sev]

        descriptions = [
            f"Heavy to very heavy rainfall expected over Bengaluru Urban district. "
            f"Citizens are advised to avoid low-lying areas.",
            f"Flash flood alert issued for parts of Bengaluru Urban. "
            f"Underpasses and storm-water drains may be inundated.",
            f"Extreme rainfall event in progress. Emergency services on standby.",
        ]

        warnings: list[dict] = []
        for i in range(n_warnings):
            sev_jitter = float(rng.uniform(-0.05, 0.05))
            warn_severity = max(0.0, min(1.0, base_severity + sev_jitter))
            issued = now_utc - timedelta(minutes=int(rng.integers(10, 60)))
            valid_until = now_utc + timedelta(hours=int(rng.integers(3, 12)))
            warnings.append({
                "warning_id": f"SYNWRN-{seed}-{i}",
                "warning_type": warning_type,
                "district": "Bengaluru Urban",
                "description": descriptions[i % len(descriptions)],
                "issued_at": issued.isoformat(),
                "valid_until": valid_until.isoformat(),
                "severity": round(warn_severity, 3),
                "source": "SYNTHETIC",
                "disclaimer": _DISCLAIMER,
            })

        logger.info(
            "SyntheticDataSource: generated %d observations, %d warnings "
            "(severity=%s, seed=%d).",
            len(observations), len(warnings), sev.value, seed,
        )
        return {"observations": observations, "warnings": warnings}
