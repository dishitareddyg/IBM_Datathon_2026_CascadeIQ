"""
app/core/errors.py
───────────────────
Custom exception hierarchy and FastAPI exception handlers for CascadeIQ.

All handlers return a consistent JSON envelope:

    {
        "error":   "GRAPH_NOT_LOADED",
        "message": "The road-network graph has not been initialised yet.",
        "detail":  { ... }          # optional context dict
    }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

# ── Exception Hierarchy ────────────────────────────────────────────────────────


class CascadeIQError(Exception):
    """
    Base exception for all CascadeIQ domain errors.

    Attributes
    ----------
    message : str
        Human-readable description of what went wrong.
    detail : dict
        Optional structured context (edge IDs, node IDs, etc.).
    http_status : int
        The HTTP status code that should be returned for this exception.
    error_code : str
        Machine-readable error code (SCREAMING_SNAKE_CASE).
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "CASCADEIQ_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail: dict[str, Any] = detail or {}

    def as_dict(self) -> dict[str, Any]:
        """Return a serialisable dict suitable for a JSON response body."""
        return {
            "error": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


class DataSourceError(CascadeIQError):
    """
    Raised when an external data source (IMD API, OSM, etc.) is unavailable
    or returns an unexpected payload.
    """

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATA_SOURCE_ERROR"

    def __init__(
        self,
        message: str = "An external data source is currently unavailable.",
        source: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = detail or {}
        if source:
            merged["source"] = source
        super().__init__(message, merged)
        self.source = source


class GraphNotLoadedError(CascadeIQError):
    """
    Raised when a route computation or graph query is attempted before the
    city road-network graph has been successfully initialised.
    """

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "GRAPH_NOT_LOADED"

    def __init__(
        self,
        message: str = "The road-network graph has not been initialised yet.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, detail)


class SimulationNotFoundError(CascadeIQError):
    """Raised when a simulation id is not in the in-memory store."""

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "SIMULATION_NOT_FOUND"

    def __init__(self, simulation_id: str, detail: dict[str, Any] | None = None) -> None:
        merged: dict[str, Any] = {"simulation_id": simulation_id}
        if detail:
            merged.update(detail)
        super().__init__(f"Simulation '{simulation_id}' was not found.", merged)
        self.simulation_id = simulation_id


class ScenarioNotFoundError(CascadeIQError):
    """
    Raised when a bundled scenario or simulation result is requested for an ID
    that does not exist in the in-memory store.
    """

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "SCENARIO_NOT_FOUND"

    def __init__(
        self,
        simulation_id: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = {"simulation_id": simulation_id}
        if detail:
            merged.update(detail)
        super().__init__(
            f"Simulation '{simulation_id}' was not found.",
            merged,
        )
        self.simulation_id = simulation_id


class ValidationError(CascadeIQError):
    """
    Raised when user-supplied inputs fail domain-level validation that
    cannot be expressed in Pydantic schemas alone (e.g., logical constraints
    across multiple fields).
    """

    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Request inputs failed domain validation.",
        field: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = detail or {}
        if field:
            merged["field"] = field
        super().__init__(message, merged)
        self.field = field


class RoutingError(CascadeIQError):
    """
    Raised when the routing engine cannot find a feasible path between two
    nodes (e.g., origin and hospital are disconnected after road closures).
    """

    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "ROUTING_ERROR"

    def __init__(
        self,
        message: str = "No feasible route exists between the requested nodes.",
        origin: str | None = None,
        destination: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = detail or {}
        if origin:
            merged["origin"] = origin
        if destination:
            merged["destination"] = destination
        super().__init__(message, merged)
        self.origin = origin
        self.destination = destination


class InfeasibleInterventionError(CascadeIQError):
    """
    Raised when a recommended intervention (reroute, divert, preposition)
    cannot be applied because the resulting assignment is infeasible given
    current road-network or resource constraints.
    """

    http_status = status.HTTP_409_CONFLICT
    error_code = "INFEASIBLE_INTERVENTION"

    def __init__(
        self,
        message: str = "The requested intervention cannot be applied under current constraints.",
        action_id: str | None = None,
        reason: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        merged: dict[str, Any] = detail or {}
        if action_id:
            merged["action_id"] = action_id
        if reason:
            merged["reason"] = reason
        super().__init__(message, merged)
        self.action_id = action_id
        self.reason = reason


# ── FastAPI Exception Handlers ─────────────────────────────────────────────────

def _json_response(exc: CascadeIQError) -> JSONResponse:
    """Convert any CascadeIQError into a structured JSONResponse."""
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.as_dict(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all CascadeIQ exception handlers on *app*.

    Call this from the application factory / main.py after creating the
    FastAPI instance.
    """

    @app.exception_handler(CascadeIQError)
    async def handle_cascadeiq_error(
        request: Request, exc: CascadeIQError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(DataSourceError)
    async def handle_data_source_error(
        request: Request, exc: DataSourceError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(GraphNotLoadedError)
    async def handle_graph_not_loaded(
        request: Request, exc: GraphNotLoadedError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(ScenarioNotFoundError)
    async def handle_scenario_not_found(
        request: Request, exc: ScenarioNotFoundError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(RoutingError)
    async def handle_routing_error(
        request: Request, exc: RoutingError
    ) -> JSONResponse:
        return _json_response(exc)

    @app.exception_handler(InfeasibleInterventionError)
    async def handle_infeasible_intervention(
        request: Request, exc: InfeasibleInterventionError
    ) -> JSONResponse:
        return _json_response(exc)
