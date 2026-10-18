"""
CascadeIQ FastAPI entrypoint.

Simulation outputs are computer-generated estimates for a student datathon.
They are not observations and not validated operational predictions.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.errors import CascadeIQError, register_exception_handlers
from app.core.logging import bind_request_id, configure_logging
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("CascadeIQ starting", extra={"study_area": settings.study_area})
    try:
        await graph_service.load()
        logger.info(
            "Road graph ready",
            extra={
                "nodes": graph_service.get().node_count(),
                "edges": graph_service.get().edge_count(),
                "source": graph_service.get().source,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Primary graph load failed (%s); bundled fallback", exc)
        graph_service.load_bundled()
    yield
    logger.info("CascadeIQ shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CascadeIQ API",
        description=(
            "Decision-support simulator for cascading urban flood emergencies in "
            "Bengaluru Urban district, Karnataka, India.\n\n"
            "**Disclaimer**: Results are simulated estimates for research and education. "
            "They do not represent actual emergency-response observations or validated "
            "real-world predictions."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        bind_request_id()
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        if elapsed_ms > settings.request_timeout_s * 1000:
            logger.warning("Request exceeded advisory timeout", extra={"path": str(request.url), "ms": elapsed_ms})
        return response

    register_exception_handlers(app)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request failed schema validation.",
                "detail": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(CascadeIQError)
    async def cascade_handler(request: Request, exc: CascadeIQError):
        return JSONResponse(status_code=exc.http_status, content=exc.as_dict())

    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
