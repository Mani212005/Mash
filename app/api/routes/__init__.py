"""
Mash Voice - API Routes Package
"""

from app.api.routes.agents import router as agents_router
from app.api.routes.calls import router as calls_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.whatsapp import router as whatsapp_router
from app.api.routes.seed import router as seed_router

__all__ = [
    "agents_router",
    "calls_router",
    "conversations_router",
    "dashboard_router",
    "knowledge_router",
    "tickets_router",
    "websocket_router",
    "whatsapp_router",
    "seed_router",
]
