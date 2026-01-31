"""
Mash Voice - Tool Implementations

Example tools for common voice agent tasks.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any

from app.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ============ Scheduling Tools ============


class CheckAvailabilityTool(BaseTool):
    """Check appointment availability."""

    name = "check_availability"
    description = "Check available appointment slots for a given date"
    
    parameters = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date to check availability (YYYY-MM-DD format)",
            },
            "service_type": {
                "type": "string",
                "description": "Type of service (optional)",
            },
        },
        "required": ["date"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        date_str = params.get("date")
        service_type = params.get("service_type", "general")
        
        self._logger.info("Checking availability", date=date_str, service=service_type)
        
        # Mock availability data
        # In production, this would query a real scheduling system
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return ToolResult(
                success=False,
                error="Invalid date format. Please use YYYY-MM-DD.",
            )
        
        # Generate mock available slots
        available_slots = []
        for hour in [9, 10, 11, 14, 15, 16]:
            if random.random() > 0.3:  # 70% chance slot is available
                available_slots.append(f"{hour}:00")
        
        if not available_slots:
            return ToolResult(
                success=True,
                data={"date": date_str, "available_slots": []},
                message=f"I'm sorry, there are no available appointments on {date_str}. Would you like to check another date?",
            )
        
        return ToolResult(
            success=True,
            data={
                "date": date_str,
                "available_slots": available_slots,
                "service_type": service_type,
            },
            message=f"We have appointments available at {', '.join(available_slots)} on {date_str}. Which time works best for you?",
        )


class BookAppointmentTool(BaseTool):
    """Book an appointment."""

    name = "book_appointment"
    description = "Book an appointment for the caller"
    
    parameters = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Appointment date (YYYY-MM-DD format)",
            },
            "time": {
                "type": "string",
                "description": "Appointment time (HH:MM format)",
            },
            "service_type": {
                "type": "string",
                "description": "Type of service",
            },
            "customer_name": {
                "type": "string",
                "description": "Customer's name",
            },
            "customer_phone": {
                "type": "string",
                "description": "Customer's phone number",
            },
            "notes": {
                "type": "string",
                "description": "Additional notes (optional)",
            },
        },
        "required": ["date", "time", "customer_name"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        date = params.get("date")
        time = params.get("time")
        customer_name = params.get("customer_name")
        
        self._logger.info(
            "Booking appointment",
            date=date,
            time=time,
            customer=customer_name,
        )
        
        # Generate confirmation number
        confirmation = "APT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # In production, this would create the appointment in a real system
        return ToolResult(
            success=True,
            data={
                "confirmation_number": confirmation,
                "date": date,
                "time": time,
                "customer_name": customer_name,
            },
            message=f"I've booked your appointment for {date} at {time}. Your confirmation number is {confirmation}. Is there anything else I can help you with?",
        )


class CancelAppointmentTool(BaseTool):
    """Cancel an existing appointment."""

    name = "cancel_appointment"
    description = "Cancel an existing appointment"
    
    parameters = {
        "type": "object",
        "properties": {
            "confirmation_number": {
                "type": "string",
                "description": "Appointment confirmation number",
            },
            "reason": {
                "type": "string",
                "description": "Reason for cancellation (optional)",
            },
        },
        "required": ["confirmation_number"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        confirmation = params.get("confirmation_number")
        
        self._logger.info("Cancelling appointment", confirmation=confirmation)
        
        # In production, this would cancel in a real system
        return ToolResult(
            success=True,
            data={"confirmation_number": confirmation, "status": "cancelled"},
            message=f"Your appointment {confirmation} has been cancelled. Would you like to reschedule?",
        )


# ============ Support Tools ============


class CreateSupportTicketTool(BaseTool):
    """Create a support ticket."""

    name = "create_support_ticket"
    description = "Create a support ticket for follow-up"
    
    parameters = {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "Brief description of the issue",
            },
            "description": {
                "type": "string",
                "description": "Detailed description of the problem",
            },
            "priority": {
                "type": "string",
                "description": "Ticket priority (low, medium, high)",
                "enum": ["low", "medium", "high"],
            },
            "customer_email": {
                "type": "string",
                "description": "Customer's email for updates",
            },
        },
        "required": ["subject", "description"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        subject = params.get("subject")
        priority = params.get("priority", "medium")
        
        self._logger.info("Creating support ticket", subject=subject, priority=priority)
        
        # Generate ticket number
        ticket_id = "TKT-" + "".join(random.choices(string.digits, k=8))
        
        return ToolResult(
            success=True,
            data={
                "ticket_id": ticket_id,
                "subject": subject,
                "priority": priority,
                "status": "open",
            },
            message=f"I've created a support ticket for you. Your ticket number is {ticket_id}. Our team will follow up within 24 hours.",
        )


class LookupCustomerTool(BaseTool):
    """Look up customer information."""

    name = "lookup_customer"
    description = "Look up customer information by phone number or email"
    
    parameters = {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Customer's phone number",
            },
            "email": {
                "type": "string",
                "description": "Customer's email address",
            },
        },
        "required": [],  # At least one should be provided
    }

    async def execute(self, **params: Any) -> ToolResult:
        phone = params.get("phone")
        email = params.get("email")
        
        if not phone and not email:
            return ToolResult(
                success=False,
                error="Please provide either a phone number or email address.",
            )
        
        self._logger.info("Looking up customer", phone=phone, email=email)
        
        # Mock customer data
        return ToolResult(
            success=True,
            data={
                "found": True,
                "customer_id": "CUST-12345",
                "name": "John Doe",
                "account_status": "active",
                "member_since": "2023-01-15",
            },
            message="I found your account. How can I help you today?",
        )


# ============ Information Tools ============


class GetBusinessHoursTool(BaseTool):
    """Get business hours."""

    name = "check_business_hours"
    description = "Get the business operating hours"
    
    parameters = {
        "type": "object",
        "properties": {
            "day": {
                "type": "string",
                "description": "Day of the week (optional)",
            },
        },
        "required": [],
    }

    async def execute(self, **params: Any) -> ToolResult:
        hours = {
            "Monday": "9:00 AM - 6:00 PM",
            "Tuesday": "9:00 AM - 6:00 PM",
            "Wednesday": "9:00 AM - 6:00 PM",
            "Thursday": "9:00 AM - 6:00 PM",
            "Friday": "9:00 AM - 5:00 PM",
            "Saturday": "10:00 AM - 2:00 PM",
            "Sunday": "Closed",
        }
        
        day = params.get("day")
        if day and day.capitalize() in hours:
            day_hours = hours[day.capitalize()]
            return ToolResult(
                success=True,
                data={"day": day.capitalize(), "hours": day_hours},
                message=f"We're open on {day.capitalize()} from {day_hours}.",
            )
        
        return ToolResult(
            success=True,
            data={"hours": hours},
            message="We're open Monday through Friday from 9 AM to 6 PM, Saturday from 10 AM to 2 PM, and closed on Sunday.",
        )


class GetCompanyInfoTool(BaseTool):
    """Get company information."""

    name = "get_company_info"
    description = "Get general company information like address, phone, services"
    
    parameters = {
        "type": "object",
        "properties": {
            "info_type": {
                "type": "string",
                "description": "Type of information needed (address, services, contact)",
            },
        },
        "required": [],
    }

    async def execute(self, **params: Any) -> ToolResult:
        info = {
            "name": "Acme Corporation",
            "address": "123 Main Street, Anytown, USA",
            "phone": "1-800-555-0123",
            "email": "info@acme.com",
            "website": "www.acme.com",
            "services": ["Consulting", "Support", "Training"],
        }
        
        return ToolResult(
            success=True,
            data=info,
            message=f"We're located at {info['address']}. You can also reach us at {info['phone']} or email us at {info['email']}.",
        )


# ============ Sales Tools ============


class GetProductInfoTool(BaseTool):
    """Get product information."""

    name = "get_product_info"
    description = "Get information about products or services"
    
    parameters = {
        "type": "object",
        "properties": {
            "product_name": {
                "type": "string",
                "description": "Name or type of product to look up",
            },
        },
        "required": ["product_name"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        product_name = params.get("product_name", "").lower()
        
        # Mock product catalog
        products = {
            "basic": {
                "name": "Basic Plan",
                "price": "$29/month",
                "features": ["5 users", "Basic support", "10GB storage"],
            },
            "professional": {
                "name": "Professional Plan",
                "price": "$79/month",
                "features": ["25 users", "Priority support", "100GB storage", "Analytics"],
            },
            "enterprise": {
                "name": "Enterprise Plan",
                "price": "Custom pricing",
                "features": ["Unlimited users", "24/7 support", "Unlimited storage", "Custom integrations"],
            },
        }
        
        for key, product in products.items():
            if key in product_name or product_name in product["name"].lower():
                return ToolResult(
                    success=True,
                    data=product,
                    message=f"The {product['name']} is {product['price']} and includes {', '.join(product['features'][:2])}. Would you like more details?",
                )
        
        return ToolResult(
            success=True,
            data={"products": list(products.values())},
            message="We offer Basic, Professional, and Enterprise plans. Which one would you like to know more about?",
        )


class CreateLeadTool(BaseTool):
    """Create a sales lead."""

    name = "create_lead"
    description = "Create a sales lead for follow-up"
    
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Lead's name",
            },
            "company": {
                "type": "string",
                "description": "Company name",
            },
            "phone": {
                "type": "string",
                "description": "Contact phone number",
            },
            "email": {
                "type": "string",
                "description": "Contact email",
            },
            "interest": {
                "type": "string",
                "description": "Product or service of interest",
            },
            "notes": {
                "type": "string",
                "description": "Additional notes",
            },
        },
        "required": ["name"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        name = params.get("name")
        interest = params.get("interest", "general inquiry")
        
        self._logger.info("Creating lead", name=name, interest=interest)
        
        lead_id = "LEAD-" + "".join(random.choices(string.digits, k=6))
        
        return ToolResult(
            success=True,
            data={
                "lead_id": lead_id,
                "name": name,
                "interest": interest,
            },
            message="Thank you for your interest! One of our sales representatives will contact you within the next business day.",
        )


# ============ Handoff Tools ============


class TransferToHumanTool(BaseTool):
    """Transfer call to human agent."""

    name = "transfer_to_human"
    description = "Transfer the call to a human agent"
    
    parameters = {
        "type": "object",
        "properties": {
            "department": {
                "type": "string",
                "description": "Department to transfer to (support, sales, billing)",
            },
            "reason": {
                "type": "string",
                "description": "Reason for transfer",
            },
            "priority": {
                "type": "string",
                "description": "Transfer priority (normal, urgent)",
            },
        },
        "required": ["reason"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        department = params.get("department", "general")
        reason = params.get("reason")
        
        self._logger.info(
            "Transferring to human",
            department=department,
            reason=reason,
        )
        
        # In production, this would initiate actual call transfer
        return ToolResult(
            success=True,
            data={
                "transfer_initiated": True,
                "department": department,
                "estimated_wait": "2 minutes",
            },
            message="I'm transferring you to a representative now. Please hold for just a moment.",
        )


class AddCallNotesTool(BaseTool):
    """Add notes to the current call."""

    name = "add_call_notes"
    description = "Add notes to the current call for human agent reference"
    
    parameters = {
        "type": "object",
        "properties": {
            "notes": {
                "type": "string",
                "description": "Notes to add to the call",
            },
            "category": {
                "type": "string",
                "description": "Note category (summary, issue, resolution)",
            },
        },
        "required": ["notes"],
    }

    async def execute(self, **params: Any) -> ToolResult:
        notes = params.get("notes")
        category = params.get("category", "general")
        
        self._logger.info("Adding call notes", category=category)
        
        return ToolResult(
            success=True,
            data={"notes_added": True, "category": category},
            message=None,  # No verbal response needed
        )


# ============ Utility Functions ============


def register_all_tools():
    """Register all built-in tools."""
    from app.tools.base_tool import get_tool_registry
    from app.tools.customer_service_tools import register_customer_service_tools
    
    registry = get_tool_registry()
    
    tools = [
        CheckAvailabilityTool(),
        BookAppointmentTool(),
        CancelAppointmentTool(),
        CreateSupportTicketTool(),
        LookupCustomerTool(),
        GetBusinessHoursTool(),
        GetCompanyInfoTool(),
        GetProductInfoTool(),
        CreateLeadTool(),
        TransferToHumanTool(),
        AddCallNotesTool(),
    ]
    
    for tool in tools:
        registry.register(tool)
    
    logger.info(f"Registered {len(tools)} built-in tools")
    
    # Register customer service tools
    register_customer_service_tools()
