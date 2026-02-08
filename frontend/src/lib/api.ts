// API Client for Mash Voice Platform

import {
  Conversation,
  Message,
  Agent,
  KnowledgeEntry,
  BusinessInfo,
  DashboardStats,
  SupportTicket,
  HealthStatus,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-a33e4.up.railway.app/api/v1';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new APIError(response.status, errorText);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) return {} as T;
  
  return JSON.parse(text) as T;
}

// Health & Status
export async function getHealth(): Promise<HealthStatus> {
  return fetchAPI<HealthStatus>('/health');
}

// Dashboard Stats
export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchAPI<DashboardStats>('/stats');
}

// Conversations
export async function getConversations(
  status?: 'active' | 'ended' | 'escalated',
  userEmail?: string
): Promise<Conversation[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (userEmail) params.set('user_email', userEmail);
  const query = params.toString();
  return fetchAPI<Conversation[]>(`/conversations${query ? `?${query}` : ''}`);
}

export async function getConversation(id: string): Promise<Conversation> {
  return fetchAPI<Conversation>(`/conversations/${id}`);
}

export async function getConversationMessages(
  conversationId: string
): Promise<Message[]> {
  return fetchAPI<Message[]>(`/conversations/${conversationId}/messages`);
}

// Agents
export async function getAgents(): Promise<Agent[]> {
  return fetchAPI<Agent[]>('/agents');
}

export async function getAgent(name: string): Promise<Agent> {
  return fetchAPI<Agent>(`/agents/${name}`);
}

// Knowledge Base
export async function getKnowledgeBase(): Promise<{
  business_info: BusinessInfo;
  faqs: KnowledgeEntry[];
}> {
  return fetchAPI('/knowledge');
}

export async function searchKnowledge(query: string): Promise<KnowledgeEntry[]> {
  const params = new URLSearchParams({ q: query });
  return fetchAPI<KnowledgeEntry[]>(`/knowledge/search?${params}`);
}

export async function addKnowledgeEntry(
  entry: Omit<KnowledgeEntry, 'id'>
): Promise<KnowledgeEntry> {
  return fetchAPI<KnowledgeEntry>('/knowledge/faqs', {
    method: 'POST',
    body: JSON.stringify(entry),
  });
}

export async function updateKnowledgeEntry(
  id: string,
  entry: Partial<KnowledgeEntry>
): Promise<KnowledgeEntry> {
  return fetchAPI<KnowledgeEntry>(`/knowledge/faqs/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(entry),
  });
}

export async function deleteKnowledgeEntry(id: string): Promise<void> {
  return fetchAPI(`/knowledge/faqs/${id}`, {
    method: 'DELETE',
  });
}

// Support Tickets
export async function getTickets(
  status?: 'open' | 'in_progress' | 'resolved' | 'closed'
): Promise<SupportTicket[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  const query = params.toString();
  return fetchAPI<SupportTicket[]>(`/tickets${query ? `?${query}` : ''}`);
}

export async function getTicket(id: string): Promise<SupportTicket> {
  return fetchAPI<SupportTicket>(`/tickets/${id}`);
}

export async function updateTicketStatus(
  id: string,
  status: SupportTicket['status']
): Promise<SupportTicket> {
  return fetchAPI<SupportTicket>(`/tickets/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// WebSocket connection for real-time updates
export function createWebSocket(
  onMessage: (data: Message) => void,
  onError?: (error: Event) => void,
  onClose?: (event: CloseEvent) => void
): WebSocket | null {
  if (typeof window === 'undefined') return null;
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/backend/api/v1/ws`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };
  
  ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
    onClose?.(event);
  };
  
  return ws;
}

// Seed Data
export async function seedConversations(count: number = 10): Promise<{ success: boolean; message: string; created_count: number }> {
  return fetchAPI(`/seed/conversations?count=${count}`, {
    method: 'POST',
  });
}

export async function clearDemoConversations(): Promise<{ success: boolean; message: string; created_count: number }> {
  return fetchAPI('/seed/conversations', {
    method: 'DELETE',
  });
}

// User Phone Management
export interface UserPhones {
  email: string;
  phone_numbers: string[];
}

export async function getUserPhones(email: string): Promise<UserPhones> {
  const params = new URLSearchParams({ email });
  return fetchAPI<UserPhones>(`/users/phones?${params}`);
}

export async function linkPhone(email: string, phoneNumber: string): Promise<UserPhones> {
  return fetchAPI<UserPhones>('/users/phones/link', {
    method: 'POST',
    body: JSON.stringify({ email, phone_number: phoneNumber }),
  });
}

export async function unlinkPhone(email: string, phoneNumber: string): Promise<UserPhones> {
  return fetchAPI<UserPhones>('/users/phones/unlink', {
    method: 'POST',
    body: JSON.stringify({ email, phone_number: phoneNumber }),
  });
}

export async function getAvailablePhones(email: string): Promise<string[]> {
  const params = new URLSearchParams({ email });
  return fetchAPI<string[]>(`/users/phones/available?${params}`);
}

// Export API object for convenient access
export const api = {
  getHealth,
  getDashboardStats,
  getConversations,
  getConversation,
  getConversationMessages,
  getAgents,
  getAgent,
  getKnowledgeBase,
  searchKnowledge,
  addKnowledgeEntry,
  updateKnowledgeEntry,
  deleteKnowledgeEntry,
  getTickets,
  getTicket,
  updateTicketStatus,
  createWebSocket,
  seedConversations,
  clearDemoConversations,
  getUserPhones,
  linkPhone,
  unlinkPhone,
  getAvailablePhones,
};

export default api;
