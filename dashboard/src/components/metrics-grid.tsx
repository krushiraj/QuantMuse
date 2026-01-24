'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PerformanceMetrics } from '@/lib/api';
import { cn } from '@/lib/utils';

interface MetricsGridProps {
  metrics: PerformanceMetrics;
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  const items = [
    { label: 'Total Return', value: formatPercent(metrics.total_return_pct), positive: metrics.total_return_pct >= 0 },
    { label: 'Win Rate', value: `${metrics.win_rate.toFixed(1)}%`, positive: metrics.win_rate >= 50 },
    { label: 'Profit Factor', value: metrics.profit_factor.toFixed(2), positive: metrics.profit_factor >= 1 },
    { label: 'Max Drawdown', value: formatPercent(-metrics.max_drawdown_pct), positive: false },
    { label: 'Total Trades', value: metrics.total_trades.toString(), neutral: true },
    { label: 'Winning Trades', value: metrics.winning_trades.toString(), positive: true },
    { label: 'Losing Trades', value: metrics.losing_trades.toString(), positive: false },
    { label: 'Avg Win', value: formatPercent(metrics.avg_win_pct), positive: true },
    { label: 'Avg Loss', value: formatPercent(metrics.avg_loss_pct), positive: false },
    { label: 'Sharpe Ratio', value: metrics.sharpe_ratio?.toFixed(2) || 'N/A', positive: (metrics.sharpe_ratio || 0) >= 1 },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {items.map((item) => (
            <div key={item.label} className="text-center p-3 rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground">{item.label}</p>
              <p
                className={cn(
                  'text-lg font-bold mt-1',
                  !item.neutral && (item.positive ? 'text-green-600' : 'text-red-600')
                )}
              >
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
