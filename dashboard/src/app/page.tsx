'use client';

import { useQuery } from '@tanstack/react-query';
import { sessionsAPI, positionsAPI, performanceAPI } from '@/lib/api';
import { useSessionStore } from '@/stores/session-store';
import { PortfolioCard } from '@/components/portfolio-card';
import { MiniEquityChart } from '@/components/mini-equity-chart';
import { RecentPositions } from '@/components/recent-positions';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { Wallet, TrendingUp, Target, Activity } from 'lucide-react';

export default function HomePage() {
  const { selectedSessionId } = useSessionStore();

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['session-summary', selectedSessionId],
    queryFn: () => sessionsAPI.getSummary(selectedSessionId!),
    enabled: !!selectedSessionId,
  });

  const { data: positions, isLoading: positionsLoading } = useQuery({
    queryKey: ['positions', selectedSessionId],
    queryFn: () => positionsAPI.list(selectedSessionId!, 'open'),
    enabled: !!selectedSessionId,
  });

  const { data: performance, isLoading: performanceLoading } = useQuery({
    queryKey: ['daily-performance', selectedSessionId],
    queryFn: () => performanceAPI.getDaily(selectedSessionId!, 30),
    enabled: !!selectedSessionId,
  });

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card className="p-8">
          <CardContent className="text-center">
            <h2 className="text-xl font-semibold mb-2">No Session Selected</h2>
            <p className="text-muted-foreground">
              Select a trading session from the dropdown above to view your portfolio.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (summaryLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[120px]" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Skeleton className="h-[280px] col-span-2" />
          <Skeleton className="h-[280px]" />
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{summary?.name}</h1>
        <p className="text-muted-foreground">Portfolio Overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <PortfolioCard
          title="Portfolio Value"
          value={formatCurrency(summary?.portfolio_value || 0)}
          subtitle={`Initial: ${formatCurrency(summary?.initial_balance || 0)}`}
          icon={<Wallet className="h-4 w-4 text-muted-foreground" />}
        />
        <PortfolioCard
          title="Total P&L"
          value={formatCurrency(summary?.total_pnl || 0)}
          subtitle={formatPercent(summary?.total_pnl_pct || 0)}
          trend={(summary?.total_pnl || 0) >= 0 ? 'up' : 'down'}
          icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
        />
        <PortfolioCard
          title="Open Positions"
          value={summary?.open_positions || 0}
          subtitle={`Invested: ${formatCurrency(summary?.invested_value || 0)}`}
          icon={<Target className="h-4 w-4 text-muted-foreground" />}
        />
        <PortfolioCard
          title="Cash Balance"
          value={formatCurrency(summary?.cash_balance || 0)}
          subtitle={`${((summary?.cash_balance || 0) / (summary?.portfolio_value || 1) * 100).toFixed(1)}% of portfolio`}
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {performance && performance.length > 0 ? (
          <MiniEquityChart data={performance} />
        ) : (
          <Card className="col-span-2">
            <CardContent className="flex items-center justify-center h-[200px]">
              <p className="text-muted-foreground">No performance data yet</p>
            </CardContent>
          </Card>
        )}
        <RecentPositions positions={positions || []} />
      </div>
    </div>
  );
}
