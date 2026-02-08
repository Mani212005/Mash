'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import {
  MessageSquare,
  Search,
  Filter,
  ArrowRight,
  Phone,
  Clock,
  Lock,
  Link2,
  Unlink,
  Plus,
  Smartphone,
} from 'lucide-react';
import { Conversation } from '@/lib/types';
import { api } from '@/lib/api';
import { cn, formatDate, formatTime, getInitials } from '@/lib/utils';

type FilterStatus = 'all' | 'active' | 'ended' | 'escalated';

export default function ConversationsPage() {
  const { data: session, status } = useSession();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [isSeeding, setIsSeeding] = useState(false);

  // Phone linking state
  const [linkedPhones, setLinkedPhones] = useState<string[]>([]);
  const [availablePhones, setAvailablePhones] = useState<string[]>([]);
  const [showLinkPanel, setShowLinkPanel] = useState(false);
  const [isLinking, setIsLinking] = useState(false);
  const [manualPhone, setManualPhone] = useState('');

  const userEmail = session?.user?.email || '';

  // Load linked phones when session changes
  useEffect(() => {
    if (!session?.user?.email) return;
    loadLinkedPhones();
  }, [session]);

  async function loadLinkedPhones() {
    try {
      const data = await api.getUserPhones(userEmail);
      setLinkedPhones(data.phone_numbers);
    } catch (err) {
      console.error('Failed to load linked phones:', err);
    }
  }

  async function loadAvailablePhones() {
    try {
      const phones = await api.getAvailablePhones(userEmail);
      setAvailablePhones(phones);
    } catch (err) {
      console.error('Failed to load available phones:', err);
    }
  }

  // Load conversations (filtered by user email)
  useEffect(() => {
    if (!session?.user?.email) {
      setIsLoading(false);
      return;
    }

    async function loadConversations() {
      try {
        setIsLoading(true);
        const filterStatus = statusFilter === 'all' ? undefined : statusFilter;
        const data = await api.getConversations(filterStatus, userEmail);
        setConversations(data);
      } catch (err) {
        console.error('Failed to load conversations:', err);
      } finally {
        setIsLoading(false);
      }
    }

    loadConversations();
  }, [statusFilter, session, linkedPhones]);

  const handleLinkPhone = async (phone: string) => {
    try {
      setIsLinking(true);
      const result = await api.linkPhone(userEmail, phone);
      setLinkedPhones(result.phone_numbers);
      await loadAvailablePhones();
    } catch (err) {
      console.error('Failed to link phone:', err);
      alert('Failed to link phone number');
    } finally {
      setIsLinking(false);
    }
  };

  const handleUnlinkPhone = async (phone: string) => {
    if (!confirm(`Unlink ${phone}? You won't see its conversations anymore.`)) return;
    try {
      setIsLinking(true);
      const result = await api.unlinkPhone(userEmail, phone);
      setLinkedPhones(result.phone_numbers);
    } catch (err) {
      console.error('Failed to unlink phone:', err);
      alert('Failed to unlink phone number');
    } finally {
      setIsLinking(false);
    }
  };

  const handleManualLink = async () => {
    const phone = manualPhone.trim();
    if (!phone) return;
    await handleLinkPhone(phone);
    setManualPhone('');
  };

  const handleOpenLinkPanel = async () => {
    setShowLinkPanel(!showLinkPanel);
    if (!showLinkPanel) {
      await loadAvailablePhones();
    }
  };

  const handleSeedData = async () => {
    try {
      setIsSeeding(true);
      await api.seedConversations(10);
      const filterStatus = statusFilter === 'all' ? undefined : statusFilter;
      const data = await api.getConversations(filterStatus, userEmail);
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
      const filterStatus = statusFilter === 'all' ? undefined : statusFilter;
      const data = await api.getConversations(filterStatus, userEmail);
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

  // Show sign-in prompt if not logged in
  if (!session) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Conversations</h1>
          <p className="text-muted-foreground mt-1">
            View and manage WhatsApp conversations
          </p>
        </div>

        <div className="bg-card border border-border rounded-xl p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">Sign in to View Conversations</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
            Conversations are linked to your Google account for privacy. Sign in to view and manage your WhatsApp bot conversations.
          </p>
          <a
            href="/login"
            className={cn(
              'inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </a>
        </div>
      </div>
    );
  }

  const getStatusBadge = (convStatus: Conversation['status']) => {
    const styles = {
      active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      escalated: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      ended: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
    };
    return styles[convStatus] || styles.ended;
  };

  // Unlinked available phones (those in available but not in linked)
  const unlinkedPhones = availablePhones.filter((p) => !linkedPhones.includes(p));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Conversations</h1>
          <p className="text-muted-foreground mt-1">
            Your WhatsApp conversations ({linkedPhones.length} linked number{linkedPhones.length !== 1 ? 's' : ''})
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleOpenLinkPanel}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2',
              showLinkPanel
                ? 'bg-primary text-primary-foreground'
                : 'bg-card border border-border text-foreground hover:bg-accent'
            )}
          >
            <Smartphone className="w-4 h-4" />
            Manage Numbers
          </button>
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

      {/* Phone Number Linking Panel */}
      {showLinkPanel && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Link2 className="w-5 h-5 text-primary" />
              Linked Phone Numbers
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Only conversations from your linked numbers will appear. Each number can only be linked to one Google account.
            </p>
          </div>

          {/* Currently linked phones */}
          {linkedPhones.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">Your Numbers</p>
              <div className="flex flex-wrap gap-2">
                {linkedPhones.map((phone) => (
                  <div
                    key={phone}
                    className="inline-flex items-center gap-2 px-3 py-2 bg-primary/10 border border-primary/20 rounded-lg"
                  >
                    <Phone className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">{phone}</span>
                    <button
                      onClick={() => handleUnlinkPhone(phone)}
                      disabled={isLinking}
                      className="ml-1 text-muted-foreground hover:text-red-500 transition-colors"
                      title="Unlink this number"
                    >
                      <Unlink className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-4 bg-accent/30 rounded-lg">
              <Phone className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                No phone numbers linked yet. Link a number to see its conversations.
              </p>
            </div>
          )}

          {/* Available phones to claim */}
          {unlinkedPhones.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">Available Numbers (from active conversations)</p>
              <div className="flex flex-wrap gap-2">
                {unlinkedPhones.map((phone) => (
                  <button
                    key={phone}
                    onClick={() => handleLinkPhone(phone)}
                    disabled={isLinking}
                    className={cn(
                      'inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
                      'bg-accent border border-border hover:bg-primary/10 hover:border-primary/30',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                  >
                    <Plus className="w-4 h-4 text-primary" />
                    <span>{phone}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Manual phone entry */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Link a Number Manually</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualPhone}
                onChange={(e) => setManualPhone(e.target.value)}
                placeholder="Enter phone number (e.g. +1234567890)"
                className={cn(
                  'flex-1 px-4 py-2 rounded-lg text-sm',
                  'bg-background border border-input',
                  'placeholder:text-muted-foreground',
                  'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary'
                )}
                onKeyDown={(e) => e.key === 'Enter' && handleManualLink()}
              />
              <button
                onClick={handleManualLink}
                disabled={isLinking || !manualPhone.trim()}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'bg-primary text-primary-foreground hover:bg-primary/90',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                Link
              </button>
            </div>
          </div>
        </div>
      )}

      {/* No linked phones prompt */}
      {linkedPhones.length === 0 && !showLinkPanel && (
        <div className="bg-card border border-border rounded-xl p-8 text-center">
          <div className="w-14 h-14 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mx-auto mb-4">
            <Smartphone className="w-7 h-7 text-amber-600 dark:text-amber-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Link Your Phone Number</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
            To see conversations, you need to link your WhatsApp phone number to your Google account.
            This ensures only you can see your conversation data.
          </p>
          <button
            onClick={handleOpenLinkPanel}
            className={cn(
              'inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            <Link2 className="w-4 h-4" />
            Manage Phone Numbers
          </button>
        </div>
      )}

      {/* Filters (only show if user has linked phones) */}
      {linkedPhones.length > 0 && (
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
            {(['all', 'active', 'escalated', 'ended'] as FilterStatus[]).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  statusFilter === s
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card border border-border text-muted-foreground hover:bg-accent'
                )}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Conversations List */}
      {linkedPhones.length > 0 && (
        <>
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
                  : 'Conversations will appear here when users message your linked WhatsApp numbers'}
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
        </>
      )}
    </div>
  );
}
