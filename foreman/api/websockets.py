
import asyncio
from fastapi import  WebSocket, WebSocketDisconnect, APIRouter
from foreman.core.ws_manager import WebSocketManager
from typing import Optional

# Global WebSocket manager - will be set by main.py
_ws_manager: Optional[WebSocketManager] = None

def set_ws_manager(manager: WebSocketManager):
    """Set the WebSocket manager instance"""
    global _ws_manager
    _ws_manager = manager

def get_ws_manager() -> Optional[WebSocketManager]:
    """Get the WebSocket manager instance"""
    return _ws_manager


# Create an APIRouter instance
router = APIRouter(
    prefix=""
)


@router.get("/api/websocket-stats")
async def get_websocket_stats():
    """Get WebSocket manager statistics"""
    ws_manager = get_ws_manager()
    if ws_manager:
        return ws_manager.get_stats()
    return {"error": "WebSocket manager not available"}


# WebSocket endpoint for dashboard updates
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            ws_manager = get_ws_manager()
            if ws_manager:
                stats = ws_manager.get_stats()
                await websocket.send_text(f"data: {stats}")
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("Dashboard WebSocket disconnected")

