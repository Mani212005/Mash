'use client';

import { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  highlight?: boolean;
}

export function StatsCard({ title, value, icon: Icon, trend, highlight }: StatsCardProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-xl p-5 transition-shadow hover:shadow-md',
        highlight && 'ring-2 ring-primary/20'
      )}
    >
      <div className="flex items-start justify-between">
        <div className={cn(
          'p-2.5 rounded-lg',
          highlight ? 'bg-primary/10' : 'bg-accent'
        )}>
          <Icon className={cn(
            'w-5 h-5',
            highlight ? 'text-primary' : 'text-muted-foreground'
          )} />
        </div>
        {trend && (
          <div className={cn(
            'flex items-center gap-0.5 text-xs font-medium',
            trend.isPositive ? 'text-green-500' : 'text-red-500'
          )}>
            {trend.isPositive ? (
              <ArrowUpRight className="w-3.5 h-3.5" />
            ) : (
              <ArrowDownRight className="w-3.5 h-3.5" />
            )}
            {trend.value}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl font-bold text-foreground">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        <p className="text-sm text-muted-foreground mt-1">{title}</p>
      </div>
    </div>
  );
}
