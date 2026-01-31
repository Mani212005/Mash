# spec.md

## Project Title

**Modular Full‑Stack Voice Agent Platform**

## Problem Statement

Existing voice‑AI platforms (Vapi, Retell, Bland, etc.) are powerful but suffer from reliability issues, limited extensibility, opaque debugging, and poor control over edge cases. This project aims to build a **bespoke,voice agent platform** that supports:

* Real phone calls via Twilio
* High‑performance ASR via Deepgram
* Multi‑agent orchestration
* Complex function calling & workflows
* Clean observability and debuggability

The system is **not for resale**, but for internal use, demos, and client projects.

---

## High‑Level Architecture

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
   ├─ TTS (Deepgram )
   └─ Webhooks & Event Store
   ↓
Twilio Audio Response

Frontend (Next.js)
   ├─ Agent Builder UI
   ├─ Call Logs & Transcripts
   ├─ Workflow Visualizer
   └─ Debug / Replay Console
```

---

## Core Features (MVP for Hackathon)

### 1. Voice Call Handling

* Inbound & outbound calls via Twilio
* Twilio Media Streams (WebSocket)
* Low‑latency audio streaming
* Call lifecycle management (start, hold, end, failure)

### 2. Speech‑to‑Text (ASR)

* Streaming ASR using Deepgram
* Support for:

  * Accents
  * Noisy environments (basic filtering)
  * Partial + final transcripts

### 3. Text‑to‑Speech (TTS)
 Deepgram TTS


### 4. Agent System

#### Agent Types

* **Primary Agent** – Default conversational agent
* **Specialist Agents** – Task‑specific (sales, support, scheduling)
* **Human Handoff Agent** – Escalation logic

#### Agent Capabilities

* Prompt‑driven behavior
* Memory (short‑term call context)
* Tool / function calling
* Agent‑to‑agent transfer

### 5. Multi‑Agent Orchestration

* Rule‑based routing (MVP)
* Context‑aware agent switching
* Explicit transfer triggers:

  * Intent detected
  * Confidence drop
  * Error / fallback

Example:

```
User intent: appointment booking
→ Transfer from GeneralAgent → SchedulerAgent
```

### 6. Function Calling & Workflows

#### Tool Calling

* JSON‑schema based tools
* Examples:

  * Book appointment
  * Fetch CRM record
  * Create ticket

#### Workflow Engine

* Step‑based execution
* Conditional branching
* Retry & fallback logic

Example Workflow:

1. Identify intent
2. Collect required slots
3. Validate inputs
4. Execute function
5. Confirm to user

---

## Backend Specification (Python)

### Tech Stack

* Python 3.11+
* FastAPI
* WebSockets
* Redis (state & sessions)
* PostgreSQL (logs & metadata)
* Celery / Background tasks (optional)

### Services

#### 1. Call Service

* Twilio webhook endpoints
* Media stream handler
* Call state tracking

#### 2. ASR Service

* Deepgram streaming client
* Transcript buffering
* Confidence scoring

#### 3. Agent Orchestrator

* Agent registry
* Routing logic
* Context injection

#### 4. Tool Executor

* Tool validation
* Permission control
* Error handling

#### 5. Event Store

* Call events
* Agent switches
* Tool invocations

---

## Frontend Specification (Next.js)

### Tech Stack

* Next.js (App Router)
* TypeScript
* TailwindCSS
* WebSockets / SSE

### Pages

#### 1. Dashboard

* Active calls
* Recent calls
* System health

#### 2. Agent Builder

* Prompt editor
* Tool assignment
* Agent routing rules

#### 3. Call Logs

* Full transcript
* Audio playback (if recorded)
* Agent timeline

#### 4. Workflow Viewer

* Visual step execution
* Errors & retries

---

## Observability & Debugging

* Per‑call trace ID
* Timeline view:

  * ASR events
  * Agent responses
  * Tool calls
* Replay mode (text‑only for MVP)

---

## Known Challenges & Design Considerations

* Twilio media stream reliability
* Latency budget (<1s target)
* Context drift across agents
* Webhook failures & retries
* Cost visibility (ASR minutes)

---

## Hackathon Scope Control

### MUST HAVE

* End‑to‑end phone call
* Single agent + one specialist agent
* One real tool call
* Live transcript UI

### NICE TO HAVE

* Agent transfer animation
* Call replay
* Provider abstraction (ASR/TTS)

### OUT OF SCOPE

* HIPAA / compliance
* Billing
* Full RAG pipelines

---

## Future Extensions

* LLM‑based agent routing
* RAG for enterprise knowledge
* Accent/noise auto‑detection
* Human‑in‑the‑loop dashboard
* Cost‑aware agent decisions

---

## Success Criteria

* Live phone demo works reliably
* Sub‑second perceived latency
* Clear multi‑agent handoff
* Easy to debug and extend

---

## TL;DR

A **clean, modular, Twilio‑first voice agent stack** that prioritizes reliability, debuggability, and multi‑agent workflows — built for real calls, not demos.
