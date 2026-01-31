'use client';

import Link from 'next/link';
import { MessageSquare, ArrowRight } from 'lucide-react';
import { Conversation } from '@/lib/types';
import { cn, formatDate, formatTime, truncate, getInitials } from '@/lib/utils';

interface RecentConversationsProps {
  conversations: Conversation[];
}

export function RecentConversations({ conversations }: RecentConversationsProps) {
  const getStatusColor = (status: Conversation['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'escalated':
        return 'bg-amber-500';
      case 'ended':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h3 className="font-semibold text-foreground">Recent Conversations</h3>
        <Link
          href="/conversations"
          className={cn(
            'text-sm text-primary hover:text-primary/80 flex items-center gap-1',
            'transition-colors'
          )}
        >
          View all
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
      
      <div className="divide-y divide-border">
        {conversations.length === 0 ? (
          <div className="p-8 text-center">
            <MessageSquare className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Start messaging via WhatsApp to see conversations here
            </p>
          </div>
        ) : (
          conversations.map((conversation) => (
            <Link
              key={conversation.id}
              href={`/conversations/${conversation.id}`}
              className="flex items-center gap-4 p-4 hover:bg-accent/50 transition-colors"
            >
              {/* Avatar */}
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-medium text-primary">
                  {getInitials(conversation.phone_number)}
                </span>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">
                    {conversation.phone_number}
                  </span>
                  <span className={cn(
                    'w-2 h-2 rounded-full',
                    getStatusColor(conversation.status)
                  )} />
                </div>
                <p className="text-sm text-muted-foreground truncate">
                  Agent: {conversation.current_agent || 'Customer Service'}
                </p>
              </div>

              {/* Meta */}
              <div className="text-right flex-shrink-0">
                <p className="text-sm text-muted-foreground">
                  {formatTime(conversation.last_message_at)}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {conversation.message_count} messages
                </p>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
