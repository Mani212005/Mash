# Mash Voice Frontend

Next.js 14 dashboard for the Mash Voice AI Customer Service Platform.

## Features

- 📊 **Dashboard** - Real-time stats and activity overview
- 💬 **Conversations** - View and manage WhatsApp conversations
- 🤖 **Agents** - Manage AI agents and their capabilities
- 📚 **Knowledge Base** - FAQs and business information management
- 🎫 **Tickets** - Support ticket management
- ⚙️ **Settings** - Configure API keys and platform settings

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Charts**: Recharts
- **Date Utils**: date-fns

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend server running on `http://localhost:8000`

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Development Commands

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Dashboard
│   │   ├── layout.tsx         # Root layout with sidebar/header
│   │   ├── conversations/     # Conversations pages
│   │   ├── agents/            # Agent management
│   │   ├── knowledge/         # Knowledge base
│   │   ├── tickets/           # Support tickets
│   │   └── settings/          # Settings page
│   ├── components/
│   │   ├── layout/            # Sidebar, Header
│   │   └── dashboard/         # Dashboard components
│   └── lib/
│       ├── api.ts             # API client
│       ├── types.ts           # TypeScript types
│       └── utils.ts           # Utility functions
├── public/                     # Static assets
├── tailwind.config.js         # Tailwind configuration
├── next.config.js             # Next.js configuration
└── package.json
```

## API Integration

The frontend proxies API requests to the backend:

- `/api/backend/*` → `http://localhost:8000/*`

Configure the backend URL in `next.config.js` if needed.

## Theme Support

Supports light and dark mode with system preference detection. Toggle in the header or configure in settings.

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Overview stats, charts, recent conversations |
| Conversations | `/conversations` | List and filter all conversations |
| Conversation Detail | `/conversations/[id]` | View message thread |
| Agents | `/agents` | View and manage AI agents |
| Knowledge Base | `/knowledge` | Manage FAQs and business info |
| Tickets | `/tickets` | Support ticket management |
| Settings | `/settings` | API keys, WhatsApp config, etc. |
