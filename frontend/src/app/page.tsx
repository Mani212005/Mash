'use client';

import { useEffect, useState } from 'react';
import {
  MessageSquare,
  Users,
  Clock,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Bot,
  Ticket,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DashboardStats, Conversation } from '@/lib/types';
import { api } from '@/lib/api';
import { StatsCard } from '@/components/dashboard/stats-card';
import { RecentConversations } from '@/components/dashboard/recent-conversations';
import { ActivityChart } from '@/components/dashboard/activity-chart';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setIsLoading(true);
        const [statsData, conversationsData] = await Promise.all([
          api.getDashboardStats().catch(() => null),
          api.getConversations().catch(() => []),
        ]);
        
        setStats(statsData || {
          total_conversations: 0,
          active_conversations: 0,
          messages_today: 0,
          avg_response_time_ms: 0,
          escalation_rate: 0,
        });
        setRecentConversations(conversationsData.slice(0, 5));
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }

    loadDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Monitor your AI customer service platform
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Conversations"
          value={stats?.total_conversations || 0}
          icon={MessageSquare}
          trend={{ value: 12, isPositive: true }}
        />
        <StatsCard
          title="Active Sessions"
          value={stats?.active_conversations || 0}
          icon={Users}
          trend={{ value: 3, isPositive: true }}
          highlight
        />
        <StatsCard
          title="Messages Today"
          value={stats?.messages_today || 0}
          icon={TrendingUp}
          trend={{ value: 8, isPositive: true }}
        />
        <StatsCard
          title="Avg Response Time"
          value={`${Math.round((stats?.avg_response_time_ms || 0) / 1000)}s`}
          icon={Clock}
          trend={{ value: 5, isPositive: false }}
        />
      </div>

      {/* Charts and Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <div className="lg:col-span-2">
          <ActivityChart />
        </div>

        {/* Quick Stats */}
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="font-semibold text-foreground mb-4">Platform Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-primary" />
                  <span className="text-sm text-muted-foreground">Active Agents</span>
                </div>
                <span className="text-sm font-medium text-foreground">4</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Ticket className="w-4 h-4 text-amber-500" />
                  <span className="text-sm text-muted-foreground">Open Tickets</span>
                </div>
                <span className="text-sm font-medium text-foreground">7</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-muted-foreground">Resolution Rate</span>
                </div>
                <span className="text-sm font-medium text-foreground">94%</span>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="font-semibold text-foreground mb-4">Escalation Rate</h3>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-foreground">
                {((stats?.escalation_rate || 0) * 100).toFixed(1)}%
              </span>
              <span className={cn(
                'text-sm font-medium flex items-center mb-1',
                'text-green-500'
              )}>
                <ArrowDownRight className="w-4 h-4" />
                2.1%
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Compared to last week
            </p>
          </div>
        </div>
      </div>

      {/* Recent Conversations */}
      <RecentConversations conversations={recentConversations} />
    </div>
  );
}
