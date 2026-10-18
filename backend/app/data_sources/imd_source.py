"""
IMD (India Meteorological Department) data source.

IMPORTANT NOTE — API AVAILABILITY
----------------------------------
The IMD does not currently expose a publicly accessible, documented REST API
for real-time rainfall or district-level weather warnings.  This module is a
**placeholder for future integration** once such an API becomes available (or
a data-sharing MoU is established with IMD).

Current behaviour
-----------------
* If ``IMD_API_KEY`` is set in application settings, the source attempts to
  call ``IMD_API_BASE_URL`` (also configurable).  Since no real endpoint
  exists yet, this call will almost certainly fail — the source catches the
  error, logs a warning, and falls back to hardcoded realistic data.
* If ``IMD_API_KEY`` is NOT set, the source immediately returns the hardcoded
  fallback data without attempting any network call.

Fallback data
-------------
Three representative rainfall observations and one weather warning are
hardcoded below.  The values are based on typical Bengaluru monsoon conditions
during the South-West monsoon season (June–September).  They are **not** real
IMD data and must not be treated as authoritative.

Sources consulted for realistic value ranges:
  * IMD Rainfall Statistics of India (2022 Annual Report, Table 4.2)
  * Karnataka SDMA rainfall bulletins (public domain, 2023 monsoon season)
  * IMD Bengaluru Meteorological Centre press releases (public domain)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.data_sources.base import DataSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback data
# Typical South-West monsoon conditions for Bengaluru Urban, Karnataka.
# Values are ILLUSTRATIVE, not real IMD data.
# ---------------------------------------------------------------------------

_FALLBACK_OBSERVATIONS: list[dict] = [
    {
        "station_id": "IMD-BLR-001",
        "station_name": "Bengaluru (HAL Airport AWS)",
        "lat": 12.9500,
        "lon": 77.6700,
        "rainfall_mm_hr": 22.4,
        "observed_at": None,        # filled dynamically with now_utc - 15 min
        "source": "IMD_FALLBACK",
        "disclaimer": (
            "FALLBACK DATA: Real IMD API unavailable. "
            "Values are representative monsoon observations and are NOT real-time data."
        ),
    },
    {
        "station_id": "IMD-BLR-002",
        "station_name": "Bengaluru (Lalbagh AWS)",
        "lat": 12.9507,
        "lon": 77.5848,
        "rainfall_mm_hr": 18.7,
        "observed_at": None,
        "source": "IMD_FALLBACK",
        "disclaimer": (
            "FALLBACK DATA: Real IMD API unavailable. "
            "Values are representative monsoon observations and are NOT real-time data."
        ),
    },
    {
        "station_id": "IMD-BLR-003",
        "station_name": "Bengaluru (Yelahanka AWS)",
        "lat": 13.1007,
        "lon": 77.5963,
        "rainfall_mm_hr": 31.2,
        "observed_at": None,
        "source": "IMD_FALLBACK",
        "disclaimer": (
            "FALLBACK DATA: Real IMD API unavailable. "
            "Values are representative monsoon observations and are NOT real-time data."
        ),
    },
]

_FALLBACK_WARNING: dict = {
    "warning_id": "IMD-WARN-FALLBACK-001",
    "warning_type": "ORANGE_ALERT",
    "district": "Bengaluru Urban",
    "description": (
        "IMD Bengaluru Meteorological Centre: Heavy to very heavy rainfall "
        "likely at isolated places over Bengaluru Urban district during the next "
        "24 hours. Thunderstorms with lightning possible."
    ),
    "issued_at": None,          # filled dynamically
    "valid_until": None,        # filled dynamically (issued_at + 24h)
    "severity": 0.65,
    "source": "IMD_FALLBACK",
    "disclaimer": (
        "FALLBACK DATA: Real IMD API unavailable. "
        "This warning is representative and is NOT an official IMD bulletin."
    ),
}


class IMDDataSource(DataSource):
    """
    IMD data source with automatic fallback to hardcoded realistic data.

    When ``IMD_API_KEY`` is present in settings, an HTTP request is attempted
    to ``IMD_API_BASE_URL``.  On failure (connection error, timeout, bad
    status), the fallback data is returned and a warning is logged.  No
    exception is ever propagated to the caller.
    """

    def __init__(self) -> None:
        self._api_key: Optional[str] = None
        self._api_base_url: str = ""
        self._load_settings()

    def _load_settings(self) -> None:
        """Load API credentials from application settings (if available)."""
        try:
            from app.core.config import get_settings  # noqa: PLC0415

            settings = get_settings()
            self._api_key = settings.imd_api_key.strip() or None
            self._api_base_url = getattr(settings, "imd_api_base_url", "") or ""
        except Exception:
            self._api_key = None
            self._api_base_url = ""

    # ------------------------------------------------------------------
    # DataSource interface
    # ------------------------------------------------------------------

    @property
    def source_name(self) -> str:
        return "IMD"

    @property
    def is_available(self) -> bool:
        """Return True only when IMD_API_KEY is set in settings."""
        return bool(self._api_key)

    async def fetch_rainfall(self, bbox: tuple) -> list[dict]:
        """
        Fetch rainfall observations from IMD API, or return fallback data.

        Parameters
        ----------
        bbox:
            ``(min_lat, min_lon, max_lat, max_lon)`` — currently passed
            through to the API if available; ignored for fallback data.
        """
        if self.is_available:
            result = await self._try_api_rainfall(bbox)
            if result is not None:
                return result
            logger.warning(
                "IMD API call failed; returning hardcoded fallback rainfall data."
            )
        else:
            logger.info(
                "IMD_API_KEY not set; IMD source unavailable. "
                "Returning hardcoded fallback rainfall data."
            )
        return self._build_fallback_observations()

    async def fetch_warnings(self, district: str) -> list[dict]:
        """
        Fetch weather warnings from IMD API, or return fallback data.

        Parameters
        ----------
        district:
            District name (e.g. ``'Bengaluru Urban'``).
        """
        if self.is_available:
            result = await self._try_api_warnings(district)
            if result is not None:
                return result
            logger.warning(
                "IMD API call failed; returning hardcoded fallback warning data."
            )
        else:
            logger.info(
                "IMD_API_KEY not set; returning hardcoded fallback warning data."
            )
        return self._build_fallback_warnings(district)

    # ------------------------------------------------------------------
    # Internal: API attempt (future integration point)
    # ------------------------------------------------------------------

    async def _try_api_rainfall(self, bbox: tuple) -> Optional[list[dict]]:
        """
        Attempt to call the IMD REST API.

        This is a **placeholder** — no real IMD public REST endpoint exists at
        the time of writing.  The method structure is provided so that a real
        implementation can be dropped in when the API becomes available.

        Returns ``None`` on any failure so the caller falls back gracefully.
        """
        try:
            import httpx   # noqa: PLC0415
            url = f"{self._api_base_url}/rainfall"
            params = {
                "api_key": self._api_key,
                "min_lat": bbox[0],
                "min_lon": bbox[1],
                "max_lat": bbox[2],
                "max_lon": bbox[3],
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                # Expected schema: {"observations": [...]}
                return data.get("observations", [])
        except Exception as exc:
            logger.debug("IMD rainfall API error: %s", exc)
            return None

    async def _try_api_warnings(self, district: str) -> Optional[list[dict]]:
        """
        Attempt to call the IMD warnings endpoint.

        Placeholder — see :meth:`_try_api_rainfall` docstring.
        Returns ``None`` on any failure.
        """
        try:
            import httpx   # noqa: PLC0415
            url = f"{self._api_base_url}/warnings"
            params = {"api_key": self._api_key, "district": district}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("warnings", [])
        except Exception as exc:
            logger.debug("IMD warnings API error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Internal: Fallback data builders
    # ------------------------------------------------------------------

    def _build_fallback_observations(self) -> list[dict]:
        """Return hardcoded observations with live-stamped timestamps."""
        now = datetime.now(timezone.utc)
        result = []
        for obs in _FALLBACK_OBSERVATIONS:
            entry = dict(obs)
            entry["observed_at"] = (now - timedelta(minutes=15)).isoformat()
            result.append(entry)
        return result

    def _build_fallback_warnings(self, district: str) -> list[dict]:
        """Return hardcoded warning with live-stamped timestamps."""
        now = datetime.now(timezone.utc)
        warning = dict(_FALLBACK_WARNING)
        warning["district"] = district
        warning["issued_at"] = (now - timedelta(hours=2)).isoformat()
        warning["valid_until"] = (now + timedelta(hours=22)).isoformat()
        return [warning]
