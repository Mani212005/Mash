"""
Mash Voice - Specialist Agents

Task-specific agents for handling particular types of requests.
"""

from typing import Any
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
    Specialist agent for technical support and customer service.
    """

    name = "support_agent"
    description = "Specialist for technical support, customer inquiries, and order help"
    agent_type = "specialist"

    def __init__(self):
        super().__init__()
        from app.services.knowledge_service import get_knowledge_service
        self._knowledge_service = get_knowledge_service()
        try:
            self._knowledge_service.load_knowledge_base()
        except Exception:
            pass

    @property
    def system_prompt(self) -> str:
        """Dynamic system prompt combining support and customer service."""
        business_info = self._knowledge_service.get_business_info() if self._knowledge_service else {}
        business_name = business_info.get("name", "our company")
        tone = business_info.get("tone", "friendly and professional")
        
        return f"""You are a helpful technical support and customer service specialist for {business_name}.

YOUR ROLE IS TO:
1. Understand the customer's problem or inquiry clearly
2. Guide through troubleshooting steps
3. Answer frequently asked questions about products, shipping, returns, etc.
4. Look up order status and tracking information
5. Help with refund requests
6. Create support tickets when needed
7. Escalate to human support when appropriate

PERSONALITY & TONE:
- Be {tone}
- Be patient, empathetic, and show understanding when customers express frustration
- Keep responses concise but helpful (suitable for both voice calls and chat messages)
- Speak naturally, avoid technical jargon, and use emojis sparingly for friendliness 😊

GUIDELINES:
1. First, understand what the customer needs.
2. For FAQs, search the knowledge base before guessing.
3. For order issues, always ask for the order ID.
4. If a customer seems frustrated or explicitly asks for a human, offer to transfer/escalate promptly.
5. Protect customer privacy - never share sensitive info.

If the issue is complex, requires policy exceptions, or the caller is frustrated, transfer to a human agent."""

    tools = [
        "lookup_order",
        "check_refund_status",
        "create_support_ticket",
        "get_ticket_status",
        "escalate_to_human",
        "search_knowledge_base",
        "get_business_hours",
        "initiate_refund",
        "lookup_customer",
        "check_system_status",
    ]
    
    transfer_rules = {
        "human": "human_handoff_agent",
        "escalate": "human_handoff_agent",
        "human_request": "human_handoff_agent",
        "sales_inquiry": "sales_agent",
    }

    async def get_greeting(self, context: CallContext) -> str:
        business_info = self._knowledge_service.get_business_info() if self._knowledge_service else {}
        business_name = business_info.get("name", "our company")
        
        # If it's a voice call (usually call_sid is not wa_ prefixed)
        if not context.call_sid.startswith("wa_"):
            return f"Hello! Thanks for calling {business_name} support. I can help you with technical issues, order status, or scheduling. What can I do for you today?"
        
        return f"👋 Hi there! Welcome to {business_name} customer support! I'm here to help you with order tracking, support tickets, returns, or technical questions. How can I help you today?"

    async def get_farewell(self, context: CallContext) -> str:
        if not context.call_sid.startswith("wa_"):
            return "Thank you for calling support. Goodbye!"
        return "Thank you for contacting us! If you need anything else, just send a message anytime. Have a great day! 😊"

    async def should_transfer(self, context: CallContext) -> str | None:
        # Transfer to human if caller seems very frustrated
        if context.sentiment in ("frustrated", "angry"):
            return "human_handoff_agent"
        return await super().should_transfer(context)

    async def process(
        self,
        user_input: str,
        context: CallContext,
        tool_definitions: list[Any] | None = None,
    ) -> Any:
        from app.utils.logging import CallLogger
        from app.agents.base_agent import AgentResponse
        log = CallLogger(context.call_sid)
        try:
            if self._should_escalate_immediately(user_input):
                return await self._handle_escalation(context, user_input)
            
            # Prepare messages
            messages = []
            for turn in context.conversation_history[-10:]:
                messages.append({
                    "role": "user" if turn.role == "user" else "assistant",
                    "content": turn.content
                })
            messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Call LLM provider abstraction
            llm_response = await self.llm_client.generate(
                messages=messages,
                system_instruction=self.system_prompt,
                tools=tool_definitions,
                temperature=0.7,
                max_output_tokens=300 if context.call_sid.startswith("wa_") else 500,
            )
            
            transfer_to = None
            if self._detect_escalation_needed(llm_response.text, context):
                transfer_to = "human_handoff_agent"
                
            return AgentResponse(
                agent_id=self.name,
                text=llm_response.text,
                tool_calls=llm_response.tool_calls,
                transfer_to=transfer_to,
                context_updates={},
            )
        except Exception as e:
            log.exception("Error in support agent process", error=str(e))
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
            "talk to human", "speak to human", "human agent", "real person",
            "talk to someone", "speak to someone", "customer service representative",
            "speak to a representative", "agent please", "transfer me",
            "connect me to", "i want to talk to", "let me speak to",
            "get me a human", "no bot", "not a bot", "real human",
        ]
        input_lower = user_input.lower()
        return any(phrase in input_lower for phrase in escalation_phrases)

    def _detect_escalation_needed(self, response_text: str, context: CallContext) -> bool:
        """Detect if escalation is needed based on conversation context."""
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
        return frustration_count >= 2

    async def _handle_escalation(self, context: CallContext, user_input: str) -> Any:
        import json
        from app.agents.base_agent import AgentResponse, ToolCall
        return AgentResponse(
            agent_id=self.name,
            text="I completely understand! Let me connect you with a human team member right away. 🔄 Transferring you now... Please hold for just a moment while I get someone to help you personally." if not context.call_sid.startswith("wa_") else """I completely understand! Let me connect you with a human team member right away. 

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
