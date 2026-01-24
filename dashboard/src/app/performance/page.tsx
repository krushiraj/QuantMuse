'use client';

import { useQuery } from '@tanstack/react-query';
import { performanceAPI } from '@/lib/api';
import { useSessionStore } from '@/stores/session-store';
import { EquityChart } from '@/components/equity-chart';
import { DrawdownChart } from '@/components/drawdown-chart';
import { MetricsGrid } from '@/components/metrics-grid';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function PerformancePage() {
  const { selectedSessionId } = useSessionStore();

  const { data: dailyData, isLoading: dailyLoading } = useQuery({
    queryKey: ['daily-performance', selectedSessionId],
    queryFn: () => performanceAPI.getDaily(selectedSessionId!, 90),
    enabled: !!selectedSessionId,
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['performance-metrics', selectedSessionId],
    queryFn: () => performanceAPI.getMetrics(selectedSessionId!),
    enabled: !!selectedSessionId,
  });

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card className="p-8">
          <CardContent className="text-center">
            <h2 className="text-xl font-semibold mb-2">No Session Selected</h2>
            <p className="text-muted-foreground">
              Select a trading session from the dropdown above to view performance.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isLoading = dailyLoading || metricsLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Performance Analytics</h1>
        <p className="text-muted-foreground">Track your trading performance over time</p>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[250px]" />
        </div>
      ) : (
        <>
          {metrics && <MetricsGrid metrics={metrics} />}

          {dailyData && dailyData.length > 0 ? (
            <>
              <EquityChart data={dailyData} />
              <DrawdownChart data={dailyData} />
            </>
          ) : (
            <Card>
              <CardContent className="flex items-center justify-center h-[300px]">
                <p className="text-muted-foreground">
                  No performance data available yet. Start trading to see your performance metrics.
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
