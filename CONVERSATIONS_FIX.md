# Conversations & Demo Data

## Problem Fixed

Your conversations weren't showing up because:
1. The API was looking for `conversation:*` keys in Redis
2. WhatsApp conversations are stored under `call:context:*` keys
3. There was no demo/example data to display

## Solution Implemented

### 1. **Fixed Conversations API** ✅
- Now checks BOTH demo conversations (`conversation:demo_*`) AND real WhatsApp conversations (`call:context:*`)
- Properly accesses Redis through StateManager
- Correctly parses conversation history from both sources

### 2. **Added Seed Data Endpoint** ✅
- **POST** `/api/v1/seed/conversations?count=10` - Create demo conversations
- **DELETE** `/api/v1/seed/conversations` - Clear demo data

### 3. **Added UI Controls** ✅
- "Add Demo Data" button - Creates 10 realistic conversations
- "Clear Demo" button - Removes all demo conversations
- Located on Conversations page header

## How to Use

### Option 1: Use the UI (Easiest)
1. Go to **Conversations** page in dashboard
2. Click **"Add Demo Data"** button
3. Wait 1-2 seconds
4. See 10 demo conversations appear!

### Option 2: Use the API
```bash
# Create 10 demo conversations
curl -X POST http://localhost:8000/api/v1/seed/conversations?count=10

# Create 25 demo conversations
curl -X POST http://localhost:8000/api/v1/seed/conversations?count=25

# Clear all demo data
curl -X DELETE http://localhost:8000/api/v1/seed/conversations
```

## What Demo Data Includes

Each demo conversation has:
- **Realistic phone numbers** (e.g., +15551234567)
- **Customer names** (John Smith, Sarah Johnson, etc.)
- **Timestamps** (spread over last 7 days)
- **Multiple messages** (2-15 messages per conversation)
- **Varied status**: active, ended, escalated
- **Different agents**: customer_service, sales, support, human_handoff
- **Realistic queries**: "What's my order status?", "I need a refund", etc.

## Example Demo Conversation

```json
{
  "id": "demo_+15551234567_1707408000",
  "phone_number": "+15551234567",
  "customer_name": "John Smith",
  "started_at": "2026-02-01T10:30:00",
  "last_message_at": "2026-02-01T10:35:00",
  "message_count": 6,
  "status": "active",
  "current_agent": "customer_service_agent",
  "messages": [
    {
      "role": "user",
      "content": "What's my order status?",
      "timestamp": "2026-02-01T10:30:00"
    },
    {
      "role": "assistant",
      "content": "Let me look that up for you!",
      "timestamp": "2026-02-01T10:30:05",
      "agent": "customer_service_agent"
    }
    // ... more messages
  ]
}
```

## Real WhatsApp Conversations

Your real WhatsApp conversations (from webhook) will also show up now! They're stored differently but the API now handles both formats.

## Data Expiration

- **Demo conversations**: Auto-delete after 7 days
- **Real conversations**: Auto-delete after 24 hours (can be changed in `state.py`)

## Files Modified

```
app/
├── api/routes/
│   ├── conversations.py    # Fixed Redis access + dual source support
│   ├── seed.py            # NEW - Demo data generator
│   └── __init__.py        # Added seed_router
├── main.py               # Registered seed_router
frontend/
└── src/
    ├── lib/api.ts         # Added seedConversations(), clearDemoConversations()
    └── app/conversations/page.tsx  # Added UI buttons
```

## Testing

1. **Start backend**: `python main.py`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Click "Add Demo Data"**
4. **See conversations populate instantly**

## Next Steps

- Real WhatsApp conversations will appear alongside demo data
- Demo data helps with:
  - UI development
  - Feature testing
  - Client demos
  - Screenshots for documentation
