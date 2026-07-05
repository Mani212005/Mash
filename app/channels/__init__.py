"""
Mash Voice - Channels Package
"""

from app.channels.base_channel import BaseChannel
from app.channels.whatsapp_channel import WhatsAppChannel

__all__ = [
    "BaseChannel",
    "WhatsAppChannel",
]
