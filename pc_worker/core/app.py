"""
FastAPI application factory for the PC worker.
"""

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..api.dashboard import add_dashboard_route
from ..api.routes import build_router

if TYPE_CHECKING:  # pragma: no cover
    from .worker import FastAPIWorker


def create_app(worker: "FastAPIWorker") -> FastAPI:
    """Create the FastAPI application bound to a worker instance."""

    app = FastAPI(
        title=f"CrowdCompute Worker - {worker.config.worker_id}",
        description="FastAPI-based worker for distributed computing",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes and dashboard
    app.include_router(build_router(worker))
    add_dashboard_route(app, worker.config.worker_id)

    return app
