"""
Mash Voice - Customer Service Tools

Tools for customer service operations like order lookup, ticket management, and escalation.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any

from app.tools.base_tool import BaseTool, ToolResult
from app.services.knowledge_service import get_knowledge_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ============ Mock Data Storage (Replace with real database in production) ============

_mock_orders: dict[str, dict] = {
    "ORD-12345": {
        "id": "ORD-12345",
        "customer_phone": "+1234567890",
        "status": "shipped",
        "items": [{"name": "Wireless Headphones", "qty": 1, "price": 79.99}],
        "total": 79.99,
        "tracking_number": "TRK-ABC123456",
        "carrier": "FedEx",
        "estimated_delivery": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "created_at": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
    },
    "ORD-67890": {
        "id": "ORD-67890",
        "customer_phone": "+1234567890",
        "status": "processing",
        "items": [
            {"name": "Phone Case", "qty": 2, "price": 19.99},
            {"name": "Screen Protector", "qty": 1, "price": 9.99},
        ],
        "total": 49.97,
        "tracking_number": None,
        "carrier": None,
        "estimated_delivery": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "created_at": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    },
}

_mock_tickets: dict[str, dict] = {}


def _generate_id(prefix: str) -> str:
    """Generate a random ID."""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


# ============ Customer Service Tools ============


class LookupOrderTool(BaseTool):
    """Look up order status and details."""

    name = "lookup_order"
    description = "Look up an order by order ID or customer phone number to get status, tracking, and details."
    
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order ID (e.g., ORD-12345)"
            },
            "phone_number": {
                "type": "string",
                "description": "Customer phone number to find their orders"
            }
        },
        "required": []
    }

    async def execute(self, **params) -> ToolResult:
        order_id = params.get("order_id")
        phone_number = params.get("phone_number")
        
        if order_id:
            # Direct order lookup
            order = _mock_orders.get(order_id)
            if order:
                return ToolResult(
                    success=True,
                    data=order,
                    message=f"Found order {order_id}"
                )
            return ToolResult(
                success=False,
                error=f"Order {order_id} not found"
            )
        
        if phone_number:
            # Find orders by phone
            customer_orders = [
                o for o in _mock_orders.values()
                if o.get("customer_phone") == phone_number
            ]
            if customer_orders:
                return ToolResult(
                    success=True,
                    data={"orders": customer_orders, "count": len(customer_orders)},
                    message=f"Found {len(customer_orders)} orders"
                )
            return ToolResult(
                success=False,
                error="No orders found for this phone number"
            )
        
        return ToolResult(
            success=False,
            error="Please provide either an order ID or phone number"
        )


class CheckRefundStatusTool(BaseTool):
    """Check the status of a refund request."""

    name = "check_refund_status"
    description = "Check the status of a refund request for an order."
    
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order ID to check refund status for"
            },
            "refund_id": {
                "type": "string",
                "description": "The refund request ID if known"
            }
        },
        "required": ["order_id"]
    }

    async def execute(self, **params) -> ToolResult:
        order_id = params.get("order_id")
        
        # Mock refund status (in production, query actual database)
        order = _mock_orders.get(order_id)
        if not order:
            return ToolResult(
                success=False,
                error=f"Order {order_id} not found"
            )
        
        # Simulate refund status
        return ToolResult(
            success=True,
            data={
                "order_id": order_id,
                "refund_status": "not_requested",
                "message": "No refund has been requested for this order. Would you like to initiate a refund?"
            }
        )


class CreateSupportTicketTool(BaseTool):
    """Create a support ticket for customer issues."""

    name = "create_support_ticket"
    description = "Create a support ticket for issues that need human follow-up."
    
    parameters = {
        "type": "object",
        "properties": {
            "customer_phone": {
                "type": "string",
                "description": "Customer's phone number"
            },
            "issue_type": {
                "type": "string",
                "enum": ["order_issue", "refund_request", "product_inquiry", "complaint", "other"],
                "description": "Type of issue"
            },
            "description": {
                "type": "string",
                "description": "Detailed description of the issue"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "Ticket priority level"
            },
            "order_id": {
                "type": "string",
                "description": "Related order ID if applicable"
            }
        },
        "required": ["customer_phone", "issue_type", "description"]
    }

    async def execute(self, **params) -> ToolResult:
        ticket_id = _generate_id("TKT")
        
        ticket = {
            "id": ticket_id,
            "customer_phone": params.get("customer_phone"),
            "issue_type": params.get("issue_type"),
            "description": params.get("description"),
            "priority": params.get("priority", "medium"),
            "order_id": params.get("order_id"),
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "assigned_to": None,
        }
        
        _mock_tickets[ticket_id] = ticket
        
        logger.info("Support ticket created", ticket_id=ticket_id)
        
        return ToolResult(
            success=True,
            data=ticket,
            message=f"Support ticket {ticket_id} created successfully. A team member will follow up within 24 hours."
        )


class GetTicketStatusTool(BaseTool):
    """Get the status of a support ticket."""

    name = "get_ticket_status"
    description = "Check the status of an existing support ticket."
    
    parameters = {
        "type": "object",
        "properties": {
            "ticket_id": {
                "type": "string",
                "description": "The support ticket ID"
            }
        },
        "required": ["ticket_id"]
    }

    async def execute(self, **params) -> ToolResult:
        ticket_id = params.get("ticket_id")
        ticket = _mock_tickets.get(ticket_id)
        
        if ticket:
            return ToolResult(
                success=True,
                data=ticket,
                message=f"Ticket {ticket_id} status: {ticket['status']}"
            )
        
        return ToolResult(
            success=False,
            error=f"Ticket {ticket_id} not found"
        )


class EscalateToHumanTool(BaseTool):
    """Escalate conversation to a human agent."""

    name = "escalate_to_human"
    description = "Transfer the conversation to a human customer service agent. Use when the customer explicitly requests human help, is very frustrated, or the issue is too complex."
    
    parameters = {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Reason for escalation"
            },
            "customer_phone": {
                "type": "string",
                "description": "Customer's phone number"
            },
            "conversation_summary": {
                "type": "string",
                "description": "Brief summary of the conversation so far"
            },
            "priority": {
                "type": "string",
                "enum": ["normal", "high", "urgent"],
                "description": "Escalation priority"
            }
        },
        "required": ["reason", "customer_phone"]
    }

    async def execute(self, **params) -> ToolResult:
        escalation_id = _generate_id("ESC")
        
        escalation = {
            "id": escalation_id,
            "reason": params.get("reason"),
            "customer_phone": params.get("customer_phone"),
            "summary": params.get("conversation_summary", ""),
            "priority": params.get("priority", "normal"),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(
            "Conversation escalated to human",
            escalation_id=escalation_id,
            reason=params.get("reason"),
        )
        
        return ToolResult(
            success=True,
            data=escalation,
            message="I'm connecting you with a human agent. Please wait a moment while I transfer you. A team member will be with you shortly."
        )


class SearchKnowledgeBaseTool(BaseTool):
    """Search the knowledge base for answers to customer questions."""

    name = "search_knowledge_base"
    description = "Search the FAQ and knowledge base to find answers to customer questions."
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The customer's question or search query"
            },
            "category": {
                "type": "string",
                "description": "Optional category to search within (e.g., 'shipping', 'returns', 'payments')"
            }
        },
        "required": ["query"]
    }

    async def execute(self, **params) -> ToolResult:
        query = params.get("query", "")
        category = params.get("category")
        
        knowledge_service = get_knowledge_service()
        
        if category:
            # Search within category
            entries = knowledge_service.get_by_category(category)
            if entries:
                return ToolResult(
                    success=True,
                    data={
                        "category": category,
                        "entries": [e.to_dict() for e in entries],
                    },
                    message=f"Found {len(entries)} entries in {category}"
                )
        
        # Semantic search
        answer, entry = await knowledge_service.find_answer(query)
        
        if answer:
            return ToolResult(
                success=True,
                data={
                    "answer": answer,
                    "source": entry.to_dict() if entry else None,
                },
                message="Found relevant information"
            )
        
        return ToolResult(
            success=False,
            error="No relevant information found in knowledge base"
        )


class GetBusinessHoursTool(BaseTool):
    """Get business operating hours."""

    name = "get_business_hours"
    description = "Get the business operating hours and contact information."
    
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, **params) -> ToolResult:
        knowledge_service = get_knowledge_service()
        
        business_info = knowledge_service.get_business_info()
        hours = business_info.get("operating_hours", {})
        contact = business_info.get("contact", {})
        
        return ToolResult(
            success=True,
            data={
                "operating_hours": hours,
                "contact": contact,
                "timezone": business_info.get("timezone", "UTC"),
            },
            message="Business hours retrieved"
        )


class InitiateRefundTool(BaseTool):
    """Initiate a refund request for an order."""

    name = "initiate_refund"
    description = "Start a refund request for an order. The refund will be processed after review."
    
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order ID to refund"
            },
            "reason": {
                "type": "string",
                "enum": ["damaged", "wrong_item", "not_as_described", "changed_mind", "late_delivery", "other"],
                "description": "Reason for refund"
            },
            "additional_details": {
                "type": "string",
                "description": "Additional details about the refund request"
            }
        },
        "required": ["order_id", "reason"]
    }

    async def execute(self, **params) -> ToolResult:
        order_id = params.get("order_id")
        reason = params.get("reason")
        
        order = _mock_orders.get(order_id)
        if not order:
            return ToolResult(
                success=False,
                error=f"Order {order_id} not found"
            )
        
        refund_id = _generate_id("REF")
        
        refund = {
            "id": refund_id,
            "order_id": order_id,
            "amount": order.get("total", 0),
            "reason": reason,
            "details": params.get("additional_details", ""),
            "status": "pending_review",
            "estimated_processing": "3-5 business days",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        logger.info("Refund initiated", refund_id=refund_id, order_id=order_id)
        
        return ToolResult(
            success=True,
            data=refund,
            message=f"Refund request {refund_id} submitted for ${order.get('total', 0):.2f}. It will be reviewed within 3-5 business days."
        )


# Export all tools
CUSTOMER_SERVICE_TOOLS = [
    LookupOrderTool,
    CheckRefundStatusTool,
    CreateSupportTicketTool,
    GetTicketStatusTool,
    EscalateToHumanTool,
    SearchKnowledgeBaseTool,
    GetBusinessHoursTool,
    InitiateRefundTool,
]


def register_customer_service_tools():
    """Register all customer service tools."""
    from app.tools import get_tool_registry
    
    registry = get_tool_registry()
    for tool_class in CUSTOMER_SERVICE_TOOLS:
        registry.register(tool_class())
    
    logger.info(f"Registered {len(CUSTOMER_SERVICE_TOOLS)} customer service tools")
