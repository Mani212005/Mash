"""
Mash Voice - API Routes Package
"""

from app.api.routes.agents import router as agents_router
from app.api.routes.calls import router as calls_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.whatsapp import router as whatsapp_router

__all__ = [
    "agents_router",
    "calls_router",
    "websocket_router",
    "whatsapp_router",
]
