"""
API routes and WebSocket endpoints for the PC worker service.
"""

from .routes import build_router
from .dashboard import add_dashboard_route, create_dashboard_html

__all__ = ["build_router", "add_dashboard_route", "create_dashboard_html"]
