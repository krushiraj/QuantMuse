'use client';

import { useQuery } from '@tanstack/react-query';
import { tradesAPI } from '@/lib/api';
import { useSessionStore } from '@/stores/session-store';
import { TradesTable } from '@/components/trades-table';
import { TradeStatsCard } from '@/components/trade-stats-card';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function TradesPage() {
  const { selectedSessionId } = useSessionStore();

  const { data: trades, isLoading: tradesLoading } = useQuery({
    queryKey: ['trades', selectedSessionId],
    queryFn: () => tradesAPI.list(selectedSessionId!),
    enabled: !!selectedSessionId,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['trade-stats', selectedSessionId],
    queryFn: () => tradesAPI.getStats(selectedSessionId!),
    enabled: !!selectedSessionId,
  });

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card className="p-8">
          <CardContent className="text-center">
            <h2 className="text-xl font-semibold mb-2">No Session Selected</h2>
            <p className="text-muted-foreground">
              Select a trading session from the dropdown above to view trades.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Trade History</h1>
        <p className="text-muted-foreground">View all your executed trades</p>
      </div>

      {statsLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
      ) : stats ? (
        <TradeStatsCard stats={stats} />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>All Trades</CardTitle>
        </CardHeader>
        <CardContent>
          {tradesLoading ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <TradesTable trades={trades || []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
