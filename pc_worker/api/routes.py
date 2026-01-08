"""
API and WebSocket routes for the PC worker service.
"""

import asyncio
import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:  # pragma: no cover
    from ..core.worker import FastAPIWorker


def build_router(worker: "FastAPIWorker") -> APIRouter:
    """Build the API router bound to a worker instance."""

    router = APIRouter()

    @router.get("/")
    async def root():
        return worker.serialize_status()

    @router.get("/stats")
    async def get_stats():
        return worker.serialize_stats()

    @router.post("/restart")
    async def restart_worker():
        await worker.restart()
        return {"message": "Worker restarted"}

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_text(json.dumps(worker.serialize_ws_status()))
                await asyncio.sleep(worker.websocket_update_interval)
        except WebSocketDisconnect:
            worker.log("Status WebSocket disconnected")

    return router
