'use client';

import { useEffect, useState } from 'react';
import {
  Bot,
  Wrench,
  Power,
  PowerOff,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Agent } from '@/lib/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  useEffect(() => {
    async function loadAgents() {
      try {
        setIsLoading(true);
        const data = await api.getAgents();
        setAgents(data);
      } catch (err) {
        console.error('Failed to load agents:', err);
        // Fallback to default agents
        setAgents([
          {
            name: 'CustomerServiceAgent',
            description: 'Handles customer inquiries, FAQs, order tracking, and general support',
            agent_type: 'primary',
            tools: [
              'search_knowledge_base',
              'get_business_info',
              'track_order',
              'check_product_availability',
              'get_store_hours',
              'create_support_ticket',
              'calculate_shipping',
              'check_return_eligibility',
            ],
            is_active: true,
          },
          {
            name: 'PrimaryAssistant',
            description: 'Main orchestrator that routes conversations to appropriate specialists',
            agent_type: 'primary',
            tools: ['transfer_to_agent', 'search', 'calculator'],
            is_active: true,
          },
          {
            name: 'ResearchAgent',
            description: 'Specializes in web research and information gathering',
            agent_type: 'specialist',
            tools: ['web_search', 'read_url'],
            is_active: true,
          },
          {
            name: 'TechSupportAgent',
            description: 'Handles technical issues and troubleshooting',
            agent_type: 'specialist',
            tools: ['search_docs', 'run_diagnostic'],
            is_active: false,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }

    loadAgents();
  }, []);

  const getAgentTypeColor = (type: Agent['agent_type']) => {
    switch (type) {
      case 'primary':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'specialist':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
      case 'handoff':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Agents</h1>
        <p className="text-muted-foreground mt-1">
          Manage your AI agents and their capabilities
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agent List */}
          <div className="lg:col-span-2 space-y-4">
            {agents.map((agent) => (
              <div
                key={agent.name}
                onClick={() => setSelectedAgent(agent)}
                className={cn(
                  'bg-card border rounded-xl p-5 cursor-pointer transition-all',
                  selectedAgent?.name === agent.name
                    ? 'border-primary ring-2 ring-primary/20'
                    : 'border-border hover:border-primary/50'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div
                      className={cn(
                        'w-12 h-12 rounded-xl flex items-center justify-center',
                        agent.is_active
                          ? 'bg-primary/10'
                          : 'bg-muted'
                      )}
                    >
                      <Bot
                        className={cn(
                          'w-6 h-6',
                          agent.is_active
                            ? 'text-primary'
                            : 'text-muted-foreground'
                        )}
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-foreground">
                          {agent.name}
                        </h3>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-xs font-medium',
                            getAgentTypeColor(agent.agent_type)
                          )}
                        >
                          {agent.agent_type}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {agent.description}
                      </p>
                      <div className="flex items-center gap-2 mt-3">
                        <Wrench className="w-3.5 h-3.5 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">
                          {agent.tools.length} tools
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {agent.is_active ? (
                      <span className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                        <Power className="w-3.5 h-3.5" />
                        Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <PowerOff className="w-3.5 h-3.5" />
                        Inactive
                      </span>
                    )}
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Agent Details */}
          <div className="lg:col-span-1">
            {selectedAgent ? (
              <div className="bg-card border border-border rounded-xl p-5 sticky top-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">
                      {selectedAgent.name}
                    </h3>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium inline-block mt-1',
                        getAgentTypeColor(selectedAgent.agent_type)
                      )}
                    >
                      {selectedAgent.agent_type}
                    </span>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mb-4">
                  {selectedAgent.description}
                </p>

                <div className="border-t border-border pt-4">
                  <h4 className="text-sm font-medium text-foreground mb-3">
                    Available Tools ({selectedAgent.tools.length})
                  </h4>
                  <div className="space-y-2">
                    {selectedAgent.tools.map((tool) => (
                      <div
                        key={tool}
                        className="flex items-center gap-2 px-3 py-2 bg-accent/50 rounded-lg"
                      >
                        <Wrench className="w-3.5 h-3.5 text-muted-foreground" />
                        <span className="text-sm text-foreground">{tool}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-border pt-4 mt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <span
                      className={cn(
                        'text-sm font-medium',
                        selectedAgent.is_active
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-muted-foreground'
                      )}
                    >
                      {selectedAgent.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <Bot className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  Select an agent to view details
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
