"""
Mash Voice - Primary Agent

The default conversational agent that handles general inquiries
and routes to specialist agents when needed.
"""

from app.agents.base_agent import BaseAgent
from app.models.schemas import CallContext


class PrimaryAgent(BaseAgent):
    """
    Primary conversational agent.
    
    This is the default agent that answers calls and handles
    general conversation. It can route to specialist agents
    based on detected intent.
    """

    name = "primary_agent"
    description = "Main conversational agent for general inquiries"
    agent_type = "primary"
    
    system_prompt = """You are a friendly and helpful voice assistant for a business.

Your role is to:
1. Greet callers warmly
2. Understand their needs
3. Help with general questions
4. Route to specialists when needed (appointments, support, sales)

Guidelines:
- Keep responses short and conversational (1-3 sentences)
- Speak naturally, as if talking to a friend
- Ask clarifying questions when needed
- Be empathetic and patient
- Avoid technical jargon
- Don't use lists or bullet points in responses

If the caller needs:
- To book an appointment → Let me transfer you to our scheduling specialist
- Technical support → Let me connect you with our support team
- Sales/pricing information → Let me get you to our sales team

Always confirm understanding before transferring."""

    tools = [
        "check_business_hours",
        "get_company_info",
    ]
    
    transfer_rules = {
        "booking": "scheduler_agent",
        "appointment": "scheduler_agent",
        "support": "support_agent",
        "technical": "support_agent",
        "sales": "sales_agent",
        "pricing": "sales_agent",
    }

    async def get_greeting(self, context: CallContext) -> str:
        """Get initial greeting."""
        return (
            "Hello! Thank you for calling. "
            "How can I help you today?"
        )

    async def get_farewell(self, context: CallContext) -> str:
        """Get farewell message."""
        return "Thank you for calling. Have a great day!"

    async def should_transfer(self, context: CallContext) -> str | None:
        """Determine if we should transfer to a specialist."""
        # Check standard transfer rules
        target = await super().should_transfer(context)
        if target:
            return target
        
        # Additional logic could be added here
        # For example, sentiment-based escalation
        if context.sentiment == "frustrated" or context.sentiment == "angry":
            return "human_handoff_agent"
        
        return None
