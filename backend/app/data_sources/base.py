"""
Abstract base class for all external data sources.

Every concrete data source must implement:
  * ``fetch_rainfall``  — spatial rainfall observations within a bounding box.
  * ``fetch_warnings``  — weather / flood warnings for a named district.
  * ``source_name``     — string identifier (e.g. ``'IMD'``, ``'SYNTHETIC'``).
  * ``is_available``    — runtime availability check (API key present, network up, …).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DataSource(ABC):
    """
    Abstract interface for weather and warning data providers.

    Subclasses must never raise unhandled exceptions from ``fetch_*`` methods —
    they should catch errors internally and return an empty list (logging the
    failure appropriately).
    """

    # ------------------------------------------------------------------
    # Data-fetching contract
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch_rainfall(self, bbox: tuple) -> list[dict]:
        """
        Return rainfall observations within *bbox*.

        Parameters
        ----------
        bbox:
            ``(min_lat, min_lon, max_lat, max_lon)`` in WGS 84.

        Returns
        -------
        list[dict]
            Each dict must contain at minimum the keys expected by the
            ``RainfallObservation`` Pydantic schema::

                {
                    "station_id": str,
                    "station_name": str,
                    "lat": float,
                    "lon": float,
                    "rainfall_mm_hr": float,
                    "observed_at": str,   # ISO-8601 UTC
                    "source": str,        # e.g. "IMD", "SYNTHETIC"
                }
        """

    @abstractmethod
    async def fetch_warnings(self, district: str) -> list[dict]:
        """
        Return active weather / flood warnings for *district*.

        Parameters
        ----------
        district:
            District name, e.g. ``'Bengaluru Urban'``.

        Returns
        -------
        list[dict]
            Each dict must contain at minimum::

                {
                    "warning_id": str,
                    "warning_type": str,  # e.g. "RED_ALERT", "ORANGE_ALERT"
                    "district": str,
                    "description": str,
                    "issued_at": str,     # ISO-8601 UTC
                    "valid_until": str,   # ISO-8601 UTC
                    "severity": float,    # 0.0–1.0
                    "source": str,
                }
        """

    # ------------------------------------------------------------------
    # Introspection contract
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable identifier for this data source."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        Runtime availability check.

        Returns ``True`` when the source can be queried (API key set, service
        reachable, etc.).  Must not raise.
        """
