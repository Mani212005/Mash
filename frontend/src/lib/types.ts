// API Types for Mash Voice Platform

export interface Conversation {
  id: string;
  phone_number: string;
  started_at: string;
  last_message_at: string;
  message_count: number;
  status: 'active' | 'ended' | 'escalated';
  current_agent: string;
  metadata?: Record<string, unknown>;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  message_type: 'text' | 'audio' | 'image' | 'interactive';
  agent?: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  result?: string;
}

export interface Agent {
  name: string;
  description: string;
  agent_type: 'primary' | 'specialist' | 'handoff';
  tools: string[];
  is_active: boolean;
}

export interface KnowledgeEntry {
  id: string;
  category: string;
  question: string;
  answer: string;
  keywords: string[];
  metadata?: Record<string, unknown>;
}

export interface BusinessInfo {
  name: string;
  tagline?: string;
  tone?: string;
  timezone?: string;
  operating_hours?: Record<string, string>;
  contact?: {
    phone?: string;
    email?: string;
    website?: string;
  };
}

export interface DashboardStats {
  total_conversations: number;
  active_conversations: number;
  messages_today: number;
  avg_response_time_ms: number;
  escalation_rate: number;
  satisfaction_score?: number;
}

export interface SupportTicket {
  id: string;
  customer_phone: string;
  issue_type: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  created_at: string;
  order_id?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  services: Record<string, string>;
}
