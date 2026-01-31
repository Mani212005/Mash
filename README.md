# Mash Voice - Modular Full-Stack Voice Agent Platform

A **clean, modular, WhatsApp-first messaging agent stack** that prioritizes reliability, debuggability, and multi-agent workflows — built for real conversations, not demos.

## Features

- 💬 **WhatsApp Integration**: Direct integration with Meta WhatsApp Business API
- 🎤 **Voice Message Support**: Transcription of voice messages using Deepgram ASR
- 🔊 **Text-to-Speech**: Low-latency TTS via Deepgram (for audio responses)
- 🤖 **Multi-Agent System**: Primary, specialist, and handoff agents with context-aware routing
- 🔧 **Function Calling**: JSON-schema based tools with workflow engine
- 📊 **Observability**: Per-conversation tracing, timeline view, and debug console

## Architecture

```
User (WhatsApp)
   ↓
Meta WhatsApp Business API
   ↓ (Webhook)
Backend (Python – FastAPI)
   ├─ WhatsApp Service (Message Handler)
   ├─ ASR (Deepgram - for voice messages)
   ├─ Agent Orchestrator
   │    ├─ Agent Router
   │    ├─ State / Context Manager
   │    └─ Workflow Engine
   ├─ Tool / Function Executor
   ├─ TTS (Deepgram)
   └─ Event Store
   ↓
WhatsApp Response
```

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (for sessions and state)
- PostgreSQL (for logs and metadata)
- Meta Developer Account with WhatsApp Business API access
- Deepgram API Key
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/mash-voice.git
cd mash-voice
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Setting Up WhatsApp Business API

1. Go to [Meta for Developers](https://developers.facebook.com/) and create an app
2. Add WhatsApp product to your app
3. Get your credentials from the WhatsApp dashboard:
   - **Phone Number ID**: Found in the WhatsApp > Getting Started section
   - **Access Token**: Generate a permanent token or use a temporary one
   - **Verify Token**: Create your own secret string for webhook verification
   - **App Secret**: Found in App Settings > Basic
4. Configure webhook:
   - Callback URL: `https://your-domain.com/api/v1/whatsapp/webhook`
   - Verify Token: Your chosen verify token
   - Subscribe to: `messages`, `messaging_postbacks`
5. For local development, use ngrok:
```bash
ngrok http 8000
```

## Project Structure

```
mash-voice/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration management
│   ├── api/
│   │   ├── routes/          # API route handlers
│   │   │   ├── whatsapp.py  # WhatsApp webhook handlers
│   │   │   ├── agents.py    # Agent management
│   │   │   ├── calls.py     # Conversation history
│   │   │   └── websocket.py # WebSocket connections
│   │   └── middleware/      # Custom middleware
│   ├── services/
│   │   ├── whatsapp_service.py  # WhatsApp API client
│   │   ├── asr_service.py       # Deepgram ASR
│   │   ├── tts_service.py       # Deepgram TTS
│   │   ├── agent_service.py     # Agent orchestration
│   │   └── tool_service.py      # Function execution
│   ├── agents/
│   │   ├── base_agent.py        # Base agent class
│   │   ├── primary_agent.py     # Default conversational agent
│   │   └── specialist_agents.py # Task-specific agents
│   ├── tools/
│   │   ├── base_tool.py         # Base tool class
│   │   └── implementations.py   # Tool implementations
│   ├── models/
│   │   ├── database.py          # SQLAlchemy models
│   │   └── schemas.py           # Pydantic schemas
│   ├── core/
│   │   ├── events.py            # Event store
│   │   ├── state.py             # State management
│   │   └── workflow.py          # Workflow engine
│   └── utils/
│       ├── logging.py           # Structured logging
│       └── audio.py             # Audio utilities
├── tests/
├── alembic/                 # Database migrations
├── pyproject.toml
└── README.md
```

## API Endpoints

### WhatsApp Webhooks
- `GET /api/v1/whatsapp/webhook` - Webhook verification (Meta challenge)
- `POST /api/v1/whatsapp/webhook` - Incoming message handler
- `POST /api/v1/whatsapp/send` - Send message (admin/testing)
- `GET /api/v1/whatsapp/health` - WhatsApp service health check

### Conversation Management
- `GET /api/v1/calls` - List conversations
- `GET /api/v1/calls/{call_id}` - Get conversation details
- `GET /api/v1/calls/{call_id}/timeline` - Event timeline
- `GET /api/v1/calls/{call_id}/transcript` - Full transcript

### Agents
- `GET /api/v1/agents` - List available agents
- `POST /api/v1/agents` - Create/update agent
- `GET /api/v1/agents/{agent_id}` - Get agent config

### Debug & Observability
- `WebSocket /api/v1/ws/{session_id}` - Live session stream

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp API Access Token | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business Phone Number ID | Yes |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | Yes |
| `WHATSAPP_APP_SECRET` | Meta App Secret for signature verification | Yes |
| `META_API_VERSION` | Meta Graph API version (default: v18.0) | No |
| `DEEPGRAM_API_KEY` | Deepgram API Key | Yes |
| `GEMINI_API_KEY` | Google Gemini API Key | Yes |
| `GEMINI_MODEL` | Gemini model (default: gemini-2.0-flash) | No |
| `REDIS_URL` | Redis connection URL | Yes |
| `DATABASE_URL` | PostgreSQL connection URL | Yes |

## WhatsApp Message Types

The platform supports the following WhatsApp message types:

| Type | Description | Handling |
|------|-------------|----------|
| Text | Regular text messages | Processed by agent |
| Audio | Voice messages | Transcribed via Deepgram, then processed |
| Interactive | Button/List replies | Extracted and processed as text |
| Image/Video | Media messages | Acknowledgment sent (coming soon) |

## Creating Custom Agents

```python
from app.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    name = "custom_agent"
    description = "A custom specialist agent"
    
    system_prompt = """
    You are a helpful specialist agent...
    """
    
    tools = ["book_appointment", "check_availability"]
    
    async def should_transfer(self, context) -> str | None:
        # Return agent name to transfer to, or None to stay
        if context.intent == "billing":
            return "billing_agent"
        return None
```

## Creating Custom Tools

```python
from app.tools.base_tool import BaseTool

class BookAppointmentTool(BaseTool):
    name = "book_appointment"
    description = "Book an appointment for the caller"
    
    parameters = {
        "type": "object",
        "properties": {
            "date": {"type": "string", "format": "date"},
            "time": {"type": "string"},
            "service": {"type": "string"}
        },
        "required": ["date", "time"]
    }
    
    async def execute(self, **params):
        # Implementation
        return {"success": True, "confirmation": "APT-12345"}
```

## Sending Interactive Messages

```python
from app.services.whatsapp_service import WhatsAppService

whatsapp = WhatsAppService()

# Send buttons
await whatsapp.send_interactive_buttons(
    to_number="1234567890",
    body_text="How can I help you today?",
    buttons=[
        {"id": "schedule", "title": "Schedule Appointment"},
        {"id": "support", "title": "Get Support"},
        {"id": "info", "title": "More Information"},
    ]
)

# Send list menu
await whatsapp.send_interactive_list(
    to_number="1234567890",
    body_text="Please select a service:",
    button_text="View Services",
    sections=[
        {
            "title": "Popular Services",
            "rows": [
                {"id": "svc1", "title": "Service 1", "description": "Description"},
                {"id": "svc2", "title": "Service 2", "description": "Description"},
            ]
        }
    ]
)
```

## Development

### Running Tests
```bash
pytest tests/ -v --cov=app
```

### Code Formatting
```bash
black app/ tests/
ruff check app/ tests/ --fix
```

### Type Checking
```bash
mypy app/
```

## Meta API Limitations

- **24-hour window**: You can only send free-form messages within 24 hours of the user's last message
- **Template messages**: To initiate conversations, use pre-approved templates
- **Rate limits**: Be aware of Meta's rate limits for your tier
- **Interactive buttons**: Maximum 3 buttons per message
- **List items**: Maximum 10 items per section

## License

MIT License - See LICENSE file for details.
