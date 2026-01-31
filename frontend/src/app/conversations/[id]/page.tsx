'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Phone,
  Bot,
  User,
  Clock,
  Wrench,
  AlertCircle,
} from 'lucide-react';
import Link from 'next/link';
import { Conversation, Message } from '@/lib/types';
import { api } from '@/lib/api';
import { cn, formatDate, formatTime } from '@/lib/utils';

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.id as string;

  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadConversation() {
      try {
        setIsLoading(true);
        const [convData, messagesData] = await Promise.all([
          api.getConversation(conversationId),
          api.getConversationMessages(conversationId),
        ]);
        setConversation(convData);
        setMessages(messagesData);
      } catch (err) {
        console.error('Failed to load conversation:', err);
      } finally {
        setIsLoading(false);
      }
    }

    if (conversationId) {
      loadConversation();
    }
  }, [conversationId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <h2 className="text-lg font-semibold text-foreground">Conversation not found</h2>
        <Link href="/conversations" className="text-primary mt-2">
          Back to conversations
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-4 pb-4 border-b border-border">
        <button
          onClick={() => router.back()}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-muted-foreground" />
        </button>
        
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Phone className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-foreground">{conversation.phone_number}</h1>
              <p className="text-sm text-muted-foreground">
                Started {formatDate(conversation.started_at)} • {conversation.message_count} messages
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={cn(
              'px-3 py-1 rounded-full text-xs font-medium',
              conversation.status === 'active'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : conversation.status === 'escalated'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
            )}
          >
            {conversation.status}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No messages in this conversation</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex gap-3',
                message.role === 'assistant' ? 'flex-row' : 'flex-row-reverse'
              )}
            >
              {/* Avatar */}
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                  message.role === 'assistant'
                    ? 'bg-primary/10'
                    : 'bg-accent'
                )}
              >
                {message.role === 'assistant' ? (
                  <Bot className="w-4 h-4 text-primary" />
                ) : (
                  <User className="w-4 h-4 text-muted-foreground" />
                )}
              </div>

              {/* Message Content */}
              <div
                className={cn(
                  'max-w-[70%] rounded-xl px-4 py-3',
                  message.role === 'assistant'
                    ? 'bg-card border border-border'
                    : 'bg-primary text-primary-foreground'
                )}
              >
                {message.agent && (
                  <p className="text-xs text-muted-foreground mb-1">
                    {message.agent}
                  </p>
                )}
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                
                {/* Tool Calls */}
                {message.tool_calls && message.tool_calls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-border">
                    {message.tool_calls.map((tool) => (
                      <div
                        key={tool.id}
                        className="flex items-center gap-2 text-xs text-muted-foreground"
                      >
                        <Wrench className="w-3 h-3" />
                        <span>{tool.name}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-1 mt-2">
                  <Clock className="w-3 h-3 text-muted-foreground opacity-60" />
                  <span className="text-xs text-muted-foreground opacity-60">
                    {formatTime(message.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Info Panel */}
      <div className="pt-4 border-t border-border">
        <div className="bg-accent/50 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Current Agent: <span className="font-medium text-foreground">{conversation.current_agent || 'Customer Service'}</span>
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            Last updated: {formatTime(conversation.last_message_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
