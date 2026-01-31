"""
Mash Voice - Specialist Agents

Task-specific agents for handling particular types of requests.
"""

from app.agents.base_agent import BaseAgent
from app.models.schemas import CallContext


class SchedulerAgent(BaseAgent):
    """
    Specialist agent for appointment scheduling.
    """

    name = "scheduler_agent"
    description = "Specialist for booking and managing appointments"
    agent_type = "specialist"
    
    system_prompt = """You are a scheduling assistant helping callers book appointments.

Your role is to:
1. Collect the necessary information for booking
2. Check availability
3. Confirm the appointment details
4. Book the appointment

Information to collect:
- Preferred date and time
- Type of service needed
- Contact information (name, phone, email)

Guidelines:
- Be efficient but friendly
- Confirm each piece of information
- Offer alternatives if preferred time is not available
- Always repeat back the final booking details
- Keep responses short and clear

Use the book_appointment and check_availability tools when appropriate."""

    tools = [
        "book_appointment",
        "check_availability",
        "cancel_appointment",
        "reschedule_appointment",
    ]

    async def get_greeting(self, context: CallContext) -> str:
        return "I can help you schedule an appointment. What date and time works best for you?"

    async def get_farewell(self, context: CallContext) -> str:
        # Check if appointment was booked
        if context.collected_slots.get("appointment_confirmed"):
            return (
                f"Your appointment is confirmed. "
                f"We'll see you then. Have a great day!"
            )
        return "Feel free to call back when you're ready to schedule. Goodbye!"


class SupportAgent(BaseAgent):
    """
    Specialist agent for technical support.
    """

    name = "support_agent"
    description = "Specialist for technical support and troubleshooting"
    agent_type = "specialist"
    
    system_prompt = """You are a technical support specialist helping callers with issues.

Your role is to:
1. Understand the problem clearly
2. Guide through troubleshooting steps
3. Create support tickets when needed
4. Escalate to human support when appropriate

Guidelines:
- Be patient and empathetic
- Use simple, non-technical language
- Walk through steps one at a time
- Confirm the issue is resolved
- Offer to create a ticket for follow-up

If the issue is complex or the caller is frustrated, offer to transfer to a human agent."""

    tools = [
        "create_support_ticket",
        "lookup_customer",
        "check_system_status",
    ]
    
    transfer_rules = {
        "human": "human_handoff_agent",
        "escalate": "human_handoff_agent",
    }

    async def get_greeting(self, context: CallContext) -> str:
        return "I'm here to help with any technical issues. What problem are you experiencing?"

    async def should_transfer(self, context: CallContext) -> str | None:
        # Transfer to human if caller seems very frustrated
        if context.sentiment in ("frustrated", "angry"):
            return "human_handoff_agent"
        return await super().should_transfer(context)


class SalesAgent(BaseAgent):
    """
    Specialist agent for sales inquiries.
    """

    name = "sales_agent"
    description = "Specialist for sales and pricing information"
    agent_type = "specialist"
    
    system_prompt = """You are a sales assistant helping potential customers.

Your role is to:
1. Understand their needs and interests
2. Provide pricing and product information
3. Answer questions about features and benefits
4. Collect contact information for follow-up
5. Schedule sales calls or demos when appropriate

Guidelines:
- Be helpful but not pushy
- Focus on how products solve their problems
- Be transparent about pricing
- Offer to schedule a detailed consultation
- Collect lead information when there's genuine interest

Use the product_info and create_lead tools when appropriate."""

    tools = [
        "get_product_info",
        "get_pricing",
        "create_lead",
        "schedule_demo",
    ]

    async def get_greeting(self, context: CallContext) -> str:
        return "I'd be happy to help with pricing and product information. What are you looking for?"


class HumanHandoffAgent(BaseAgent):
    """
    Agent that handles handoff to human operators.
    """

    name = "human_handoff_agent"
    description = "Handles escalation to human operators"
    agent_type = "handoff"
    
    system_prompt = """You are preparing to transfer the caller to a human representative.

Your role is to:
1. Acknowledge the caller's need for human assistance
2. Collect key information to help the human agent
3. Set expectations about wait times
4. Keep the caller informed during the transfer

Guidelines:
- Be empathetic and reassuring
- Thank them for their patience
- Briefly summarize the issue before transfer
- Let them know a human will be with them shortly"""

    tools = [
        "transfer_to_human",
        "check_agent_availability",
        "add_call_notes",
    ]

    async def get_greeting(self, context: CallContext) -> str:
        return (
            "I understand you'd like to speak with a person. "
            "Let me connect you with one of our team members. "
            "Before I do, could you briefly describe what you need help with?"
        )

    async def should_transfer(self, context: CallContext) -> str | None:
        # This agent doesn't transfer to other AI agents
        return None
