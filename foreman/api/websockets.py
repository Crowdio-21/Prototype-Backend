
import asyncio
from fastapi import  WebSocket, WebSocketDisconnect, APIRouter
from foreman.core.websocket_manager import WebSocketManager

# Global WebSocket manager
ws_manager: WebSocketManager = None


# Create an APIRouter instance
router = APIRouter(
    prefix=""
)


@router.get("/api/websocket-stats")
async def get_websocket_stats():
    """Get WebSocket manager statistics"""
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
            if ws_manager:
                stats = ws_manager.get_stats()
                await websocket.send_text(f"data: {stats}")
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("Dashboard WebSocket disconnected")

