'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  MessageSquare,
  Search,
  Filter,
  ArrowRight,
  Phone,
  Clock,
} from 'lucide-react';
import { Conversation } from '@/lib/types';
import { api } from '@/lib/api';
import { cn, formatDate, formatTime, getInitials } from '@/lib/utils';

type FilterStatus = 'all' | 'active' | 'ended' | 'escalated';

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [isSeeding, setIsSeeding] = useState(false);

  useEffect(() => {
    async function loadConversations() {
      try {
        setIsLoading(true);
        const status = statusFilter === 'all' ? undefined : statusFilter;
        const data = await api.getConversations(status);
        setConversations(data);
      } catch (err) {
        console.error('Failed to load conversations:', err);
      } finally {
        setIsLoading(false);
      }
    }

    loadConversations();
  }, [statusFilter]);

  const handleSeedData = async () => {
    try {
      setIsSeeding(true);
      await api.seedConversations(10);
      // Reload conversations
      const status = statusFilter === 'all' ? undefined : statusFilter;
      const data = await api.getConversations(status);
      setConversations(data);
    } catch (err) {
      console.error('Failed to seed conversations:', err);
      alert('Failed to create demo data');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleClearDemo = async () => {
    if (!confirm('Clear all demo conversations?')) return;
    try {
      setIsSeeding(true);
      await api.clearDemoConversations();
      // Reload conversations
      const status = statusFilter === 'all' ? undefined : statusFilter;
      const data = await api.getConversations(status);
      setConversations(data);
    } catch (err) {
      console.error('Failed to clear demo data:', err);
      alert('Failed to clear demo data');
    } finally {
      setIsSeeding(false);
    }
  };

  const filteredConversations = conversations.filter((conv) => {
    if (!searchQuery) return true;
    return conv.phone_number.includes(searchQuery) ||
      conv.current_agent?.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const getStatusBadge = (status: Conversation['status']) => {
    const styles = {
      active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      escalated: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      ended: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
    };
    return styles[status] || styles.ended;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Conversations</h1>
          <p className="text-muted-foreground mt-1">
            View and manage WhatsApp conversations
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleClearDemo}
            disabled={isSeeding || conversations.length === 0}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-red-600 text-white hover:bg-red-700',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            Clear Demo
          </button>
          <button
            onClick={handleSeedData}
            disabled={isSeeding}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isSeeding ? 'Loading...' : 'Add Demo Data'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by phone number or agent..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2 rounded-lg text-sm',
              'bg-background border border-input',
              'placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
            )}
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          {(['all', 'active', 'escalated', 'ended'] as FilterStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                statusFilter === status
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border text-muted-foreground hover:bg-accent'
              )}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Conversations List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredConversations.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center">
          <MessageSquare className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold text-foreground mb-2">No conversations found</h3>
          <p className="text-sm text-muted-foreground">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Conversations will appear here when users message via WhatsApp'}
          </p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-accent/50">
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Contact
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Status
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Agent
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Messages
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Last Activity
                  </th>
                  <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredConversations.map((conversation) => (
                  <tr
                    key={conversation.id}
                    className="hover:bg-accent/30 transition-colors"
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {getInitials(conversation.phone_number)}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-foreground">
                            {conversation.phone_number}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Started {formatDate(conversation.started_at)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={cn(
                          'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium',
                          getStatusBadge(conversation.status)
                        )}
                      >
                        {conversation.status}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className="text-sm text-foreground">
                        {conversation.current_agent || 'Customer Service'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className="text-sm text-foreground">
                        {conversation.message_count}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Clock className="w-3.5 h-3.5" />
                        {formatTime(conversation.last_message_at)}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <Link
                        href={`/conversations/${conversation.id}`}
                        className={cn(
                          'inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80',
                          'transition-colors'
                        )}
                      >
                        View
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
