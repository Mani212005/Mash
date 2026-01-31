"""
Mash Voice - Customer Service Agent

AI-powered customer service chatbot agent that handles inquiries,
order lookups, FAQ responses, and escalation to human agents.
"""

from typing import Any
import json

from google import genai
from google.genai import types

from app.agents.base_agent import BaseAgent, AgentResponse, ToolCall
from app.config import get_settings
from app.models.schemas import CallContext, ToolDefinition
from app.services.knowledge_service import get_knowledge_service
from app.utils.logging import CallLogger, get_logger

logger = get_logger(__name__)


class CustomerServiceAgent(BaseAgent):
    """
    Customer Service chatbot agent.
    
    Handles:
    - FAQ inquiries
    - Order status lookups
    - Refund requests
    - Complaint handling
    - Human escalation
    """

    name = "customer_service_agent"
    description = "AI customer service agent for handling inquiries, orders, and support"
    agent_type = "primary"
    
    # Tools available to this agent
    tools = [
        "lookup_order",
        "check_refund_status",
        "create_support_ticket",
        "get_ticket_status",
        "escalate_to_human",
        "search_knowledge_base",
        "get_business_hours",
        "initiate_refund",
    ]
    
    # Transfer rules
    transfer_rules = {
        "human_request": "human_handoff_agent",
        "sales_inquiry": "sales_agent",
    }

    def __init__(self):
        super().__init__()
        self._knowledge_service = get_knowledge_service()
        self._settings = get_settings()
        
        # Load business info for personalization
        self._business_name = self._knowledge_service.get_business_info("name") or "our company"

    @property
    def system_prompt(self) -> str:
        """Dynamic system prompt with business context."""
        business_info = self._knowledge_service.get_business_info()
        business_name = business_info.get("name", "our company")
        tone = business_info.get("tone", "friendly and professional")
        
        return f"""You are a helpful AI customer service assistant for {business_name}.

PERSONALITY & TONE:
- Be {tone}
- Show empathy when customers express frustration
- Keep responses concise but helpful (this is WhatsApp, not email)
- Use emojis sparingly for friendliness 😊
- Always be honest - if you can't help with something, say so

CAPABILITIES:
- Answer frequently asked questions about products, shipping, returns, etc.
- Look up order status and tracking information
- Help with refund requests
- Create support tickets for complex issues
- Escalate to human agents when needed

GUIDELINES:
1. First, try to understand what the customer needs
2. For FAQs, search the knowledge base before making up answers
3. For order issues, always ask for the order ID
4. If a customer seems frustrated or explicitly asks for a human, escalate promptly
5. Never make promises about refunds/compensation without using the proper tools
6. Protect customer privacy - never share sensitive info

ESCALATION TRIGGERS - Transfer to human when:
- Customer explicitly asks for a human
- Customer expresses strong frustration (after attempting to help)
- Issue requires policy exceptions
- Technical issues you cannot resolve
- Complaints about AI service

Remember: You're chatting on WhatsApp, so keep messages short and mobile-friendly."""

    async def get_greeting(self, context: CallContext) -> str:
        """Get personalized greeting."""
        business_info = self._knowledge_service.get_business_info()
        business_name = business_info.get("name", "our company")
        
        return f"""👋 Hi there! Welcome to {business_name} customer support!

I'm your AI assistant and I'm here to help you with:
• Order tracking & status
• Returns & refunds
• Product questions
• General inquiries

How can I help you today?"""

    async def get_farewell(self, context: CallContext) -> str:
        """Get farewell message."""
        return """Thank you for contacting us! 🙏

If you need anything else, just send a message anytime. Have a great day! 😊"""

    async def process(
        self,
        user_input: str,
        context: CallContext,
        tool_definitions: list[ToolDefinition] | None = None,
    ) -> AgentResponse:
        """
        Process customer message and generate response.
        
        Overrides base class to add customer service specific logic.
        """
        log = CallLogger(context.call_sid)
        
        try:
            # Check for explicit escalation request
            if self._should_escalate_immediately(user_input):
                return await self._handle_escalation(context, user_input)
            
            # Build conversation for Gemini
            contents = self._build_gemini_contents(user_input, context)
            
            # Prepare tools
            gemini_tools = None
            if tool_definitions:
                function_declarations = [
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters=t.parameters,
                    )
                    for t in tool_definitions
                ]
                gemini_tools = [types.Tool(function_declarations=function_declarations)]
            
            log.debug("Processing customer message", input_length=len(user_input))
            
            # Call Gemini
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=300,  # Keep responses short for WhatsApp
                system_instruction=self.system_prompt,
                tools=gemini_tools,
            )
            
            response = await self._gemini_client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=contents,
                config=config,
            )
            
            # Process response
            tool_calls = []
            text = ""
            
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text += part.text
                    elif part.function_call:
                        fc = part.function_call
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{fc.name}_{len(tool_calls)}",
                                name=fc.name,
                                arguments=json.dumps(dict(fc.args)) if fc.args else "{}",
                            )
                        )
            
            # Check if we should escalate based on response
            transfer_to = None
            if self._detect_escalation_needed(text, context):
                transfer_to = "human_handoff_agent"
            
            log.info(
                "Customer service response",
                response_length=len(text),
                tool_calls=len(tool_calls),
                escalate=transfer_to is not None,
            )
            
            return AgentResponse(
                agent_id=self.name,
                text=text,
                tool_calls=tool_calls,
                transfer_to=transfer_to,
                context_updates={},
            )
            
        except Exception as e:
            log.exception("Error in customer service agent", error=str(e))
            return AgentResponse(
                agent_id=self.name,
                text="I apologize, I'm having a technical issue. Let me connect you with a team member who can help. One moment please! 🙏",
                tool_calls=[],
                transfer_to="human_handoff_agent",
                error=str(e),
            )

    def _should_escalate_immediately(self, user_input: str) -> bool:
        """Check if user explicitly wants human assistance."""
        escalation_phrases = [
            "talk to human",
            "speak to human",
            "human agent",
            "real person",
            "talk to someone",
            "speak to someone",
            "customer service representative",
            "speak to a representative",
            "agent please",
            "transfer me",
            "connect me to",
            "i want to talk to",
            "let me speak to",
            "get me a human",
            "no bot",
            "not a bot",
            "real human",
        ]
        
        input_lower = user_input.lower()
        return any(phrase in input_lower for phrase in escalation_phrases)

    def _detect_escalation_needed(self, response_text: str, context: CallContext) -> bool:
        """Detect if escalation is needed based on conversation context."""
        # Check conversation history for frustration signals
        frustration_count = 0
        
        for turn in context.conversation_history[-5:]:
            if turn.role == "user":
                content_lower = turn.content.lower()
                if any(word in content_lower for word in [
                    "frustrated", "angry", "ridiculous", "unacceptable",
                    "waste of time", "useless", "terrible", "worst",
                    "lawsuit", "bbb", "complaint", "manager"
                ]):
                    frustration_count += 1
        
        # Escalate if multiple frustration signals
        return frustration_count >= 2

    async def _handle_escalation(self, context: CallContext, user_input: str) -> AgentResponse:
        """Handle immediate escalation request."""
        return AgentResponse(
            agent_id=self.name,
            text="""I completely understand! Let me connect you with a human team member right away. 

🔄 Transferring you now...

Please hold for just a moment while I get someone to help you personally.""",
            tool_calls=[
                ToolCall(
                    id="escalate_1",
                    name="escalate_to_human",
                    arguments=json.dumps({
                        "reason": "Customer requested human agent",
                        "customer_phone": context.metadata.get("phone_number", "unknown"),
                        "conversation_summary": f"Customer explicitly requested human assistance. Last message: {user_input[:100]}",
                        "priority": "high",
                    }),
                )
            ],
            transfer_to="human_handoff_agent",
            context_updates={"escalation_reason": "customer_request"},
        )

    async def handle_tool_result(
        self,
        tool_name: str,
        result: dict[str, Any],
        context: CallContext,
    ) -> str:
        """
        Generate a customer-friendly response based on tool results.
        
        Args:
            tool_name: Name of the tool that was executed
            result: Tool execution result
            context: Call context
            
        Returns:
            Formatted response message
        """
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return f"I'm sorry, I couldn't complete that: {error}. Would you like me to try something else?"
        
        data = result.get("data", {})
        
        if tool_name == "lookup_order":
            if "orders" in data:
                # Multiple orders
                orders = data["orders"]
                response = f"📦 I found {len(orders)} order(s):\n\n"
                for order in orders[:3]:  # Limit to 3
                    response += f"• **{order['id']}** - {order['status'].title()}\n"
                return response + "\nWhich order would you like details about?"
            else:
                # Single order
                status_emoji = {
                    "processing": "⏳",
                    "shipped": "🚚",
                    "delivered": "✅",
                    "cancelled": "❌",
                }.get(data.get("status"), "📦")
                
                response = f"""{status_emoji} **Order {data['id']}**

Status: {data['status'].title()}
Total: ${data.get('total', 0):.2f}"""
                
                if data.get("tracking_number"):
                    response += f"\nTracking: {data['tracking_number']} ({data.get('carrier', 'N/A')})"
                if data.get("estimated_delivery"):
                    response += f"\nEstimated Delivery: {data['estimated_delivery']}"
                
                return response
        
        elif tool_name == "create_support_ticket":
            return f"""✅ I've created a support ticket for you!

**Ticket ID:** {data.get('id')}
**Priority:** {data.get('priority', 'medium').title()}

A team member will follow up within 24 hours. Is there anything else I can help with?"""
        
        elif tool_name == "initiate_refund":
            return f"""💰 Refund request submitted!

**Refund ID:** {data.get('id')}
**Amount:** ${data.get('amount', 0):.2f}
**Processing Time:** {data.get('estimated_processing', '3-5 business days')}

You'll receive a confirmation once it's processed. Anything else?"""
        
        elif tool_name == "search_knowledge_base":
            if data.get("answer"):
                return data["answer"]
            return "I couldn't find specific information about that. Would you like me to create a support ticket?"
        
        elif tool_name == "get_business_hours":
            hours = data.get("operating_hours", {})
            contact = data.get("contact", {})
            
            response = "🕐 **Business Hours:**\n"
            for day, time in hours.items():
                response += f"• {day}: {time}\n"
            
            if contact:
                response += f"\n📞 Phone: {contact.get('phone', 'N/A')}"
                response += f"\n📧 Email: {contact.get('email', 'N/A')}"
            
            return response
        
        # Default response
        return result.get("message", "Done! Is there anything else you need?")
