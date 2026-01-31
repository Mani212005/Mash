'use client';

import { useEffect, useState } from 'react';
import {
  Ticket,
  Search,
  Filter,
  Clock,
  User,
  AlertTriangle,
  CheckCircle,
  Circle,
  ArrowUpRight,
} from 'lucide-react';
import { SupportTicket } from '@/lib/types';
import { api } from '@/lib/api';
import { cn, formatDate, formatTime } from '@/lib/utils';

type TicketFilter = 'all' | 'open' | 'in_progress' | 'resolved' | 'closed';

export default function TicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<TicketFilter>('all');

  useEffect(() => {
    async function loadTickets() {
      try {
        setIsLoading(true);
        const status = statusFilter === 'all' ? undefined : statusFilter;
        const data = await api.getTickets(status as SupportTicket['status']);
        setTickets(data);
      } catch (err) {
        console.error('Failed to load tickets:', err);
        // Fallback data
        setTickets([
          {
            id: 'TKT-001',
            customer_phone: '+1234567890',
            issue_type: 'order_issue',
            description: 'Order not delivered yet, tracking shows it arrived 2 days ago',
            priority: 'high',
            status: 'open',
            created_at: new Date().toISOString(),
            order_id: 'ORD-12345',
          },
          {
            id: 'TKT-002',
            customer_phone: '+0987654321',
            issue_type: 'refund',
            description: 'Requesting refund for damaged product',
            priority: 'medium',
            status: 'in_progress',
            created_at: new Date(Date.now() - 86400000).toISOString(),
            order_id: 'ORD-12346',
          },
          {
            id: 'TKT-003',
            customer_phone: '+1122334455',
            issue_type: 'general',
            description: 'Question about warranty coverage',
            priority: 'low',
            status: 'resolved',
            created_at: new Date(Date.now() - 172800000).toISOString(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }

    loadTickets();
  }, [statusFilter]);

  const getPriorityBadge = (priority: SupportTicket['priority']) => {
    const styles = {
      urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    };
    return styles[priority];
  };

  const getStatusIcon = (status: SupportTicket['status']) => {
    switch (status) {
      case 'open':
        return <Circle className="w-4 h-4 text-blue-500" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-amber-500" />;
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'closed':
        return <CheckCircle className="w-4 h-4 text-gray-400" />;
      default:
        return <Circle className="w-4 h-4" />;
    }
  };

  const filteredTickets = tickets.filter((ticket) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      ticket.id.toLowerCase().includes(query) ||
      ticket.customer_phone.includes(query) ||
      ticket.description.toLowerCase().includes(query) ||
      ticket.order_id?.toLowerCase().includes(query)
    );
  });

  const stats = {
    open: tickets.filter((t) => t.status === 'open').length,
    in_progress: tickets.filter((t) => t.status === 'in_progress').length,
    resolved: tickets.filter((t) => t.status === 'resolved').length,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Support Tickets</h1>
        <p className="text-muted-foreground mt-1">
          Manage escalated customer issues
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Open Tickets</p>
              <p className="text-2xl font-bold text-foreground mt-1">{stats.open}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Circle className="w-5 h-5 text-blue-500" />
            </div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">In Progress</p>
              <p className="text-2xl font-bold text-foreground mt-1">{stats.in_progress}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Resolved Today</p>
              <p className="text-2xl font-bold text-foreground mt-1">{stats.resolved}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search tickets..."
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
          {(['all', 'open', 'in_progress', 'resolved'] as TicketFilter[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                statusFilter === status
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border text-muted-foreground hover:bg-accent'
              )}
            >
              {status === 'in_progress' ? 'In Progress' : status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Tickets List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredTickets.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center">
          <Ticket className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold text-foreground mb-2">No tickets found</h3>
          <p className="text-sm text-muted-foreground">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'No support tickets have been created yet'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTickets.map((ticket) => (
            <div
              key={ticket.id}
              className="bg-card border border-border rounded-xl p-4 hover:border-primary/50 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  {getStatusIcon(ticket.status)}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{ticket.id}</span>
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-medium',
                          getPriorityBadge(ticket.priority)
                        )}
                      >
                        {ticket.priority}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {ticket.description}
                    </p>
                    <div className="flex items-center gap-4 mt-2">
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <User className="w-3.5 h-3.5" />
                        {ticket.customer_phone}
                      </span>
                      {ticket.order_id && (
                        <span className="text-xs text-muted-foreground">
                          Order: {ticket.order_id}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatDate(ticket.created_at)}
                      </span>
                    </div>
                  </div>
                </div>

                <button className="p-2 rounded-lg hover:bg-accent transition-colors">
                  <ArrowUpRight className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
