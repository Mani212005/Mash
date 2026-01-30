# Mash Voice - Modular Full-Stack Voice Agent Platform

A **clean, modular, Twilio-first voice agent stack** that prioritizes reliability, debuggability, and multi-agent workflows — built for real calls, not demos.

## Features

- 📞 **Voice Call Handling**: Inbound & outbound calls via Twilio with WebSocket media streams
- 🎤 **Speech-to-Text**: Streaming ASR using Deepgram with accent and noise support
- 🔊 **Text-to-Speech**: Low-latency TTS via Deepgram
- 🤖 **Multi-Agent System**: Primary, specialist, and handoff agents with context-aware routing
- 🔧 **Function Calling**: JSON-schema based tools with workflow engine
- 📊 **Observability**: Per-call tracing, timeline view, and debug console

## Architecture

```
Caller (Phone)
   ↓
Twilio Voice Call
   ↓ (Media Stream / WebSocket)
Backend (Python – FastAPI)
   ├─ ASR (Deepgram Streaming)
   ├─ Agent Orchestrator
   │    ├─ Agent Router
   │    ├─ State / Context Manager
   │    └─ Workflow Engine
   ├─ Tool / Function Executor
   ├─ TTS (Deepgram)
   └─ Webhooks & Event Store
   ↓
Twilio Audio Response
```

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (for sessions and state)
- PostgreSQL (for logs and metadata)
- Twilio Account
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

### Setting Up Twilio

1. Create a Twilio account and get a phone number
2. Configure your webhook URL in Twilio Console:
   - Voice URL: `https://your-domain.com/api/v1/twilio/voice`
   - Status Callback: `https://your-domain.com/api/v1/twilio/status`
3. For local development, use ngrok:
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
│   │   └── middleware/      # Custom middleware
│   ├── services/
│   │   ├── call_service.py      # Twilio call handling
│   │   ├── asr_service.py       # Deepgram ASR
│   │   ├── tts_service.py       # Deepgram TTS
│   │   ├── agent_service.py     # Agent orchestration
│   │   └── tool_service.py      # Function execution
│   ├── agents/
│   │   ├── base_agent.py        # Base agent class
│   │   ├── primary_agent.py     # Default conversational agent
│   │   └── specialist_agents/   # Task-specific agents
│   ├── tools/
│   │   ├── base_tool.py         # Base tool class
│   │   └── implementations/     # Actual tool implementations
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

### Twilio Webhooks
- `POST /api/v1/twilio/voice` - Initial call webhook
- `POST /api/v1/twilio/status` - Call status updates
- `WebSocket /api/v1/twilio/stream/{call_sid}` - Media stream

### Call Management
- `GET /api/v1/calls` - List calls
- `GET /api/v1/calls/{call_id}` - Get call details
- `POST /api/v1/calls/outbound` - Initiate outbound call
- `POST /api/v1/calls/{call_id}/end` - End active call

### Agents
- `GET /api/v1/agents` - List available agents
- `POST /api/v1/agents` - Create/update agent
- `GET /api/v1/agents/{agent_id}` - Get agent config

### Debug & Observability
- `GET /api/v1/calls/{call_id}/timeline` - Call event timeline
- `GET /api/v1/calls/{call_id}/transcript` - Full transcript
- `WebSocket /api/v1/calls/{call_id}/live` - Live call stream

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes |
| `DEEPGRAM_API_KEY` | Deepgram API Key | Yes |
| `OPENAI_API_KEY` | OpenAI API Key | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `DATABASE_URL` | PostgreSQL connection URL | Yes |

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

## License

MIT License - See LICENSE file for details.
