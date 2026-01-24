'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TradeStats } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TradeStatsCardProps {
  stats: TradeStats;
}

export function TradeStatsCard({ stats }: TradeStatsCardProps) {
  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Win Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.win_rate.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            {stats.winning_trades}W / {stats.losing_trades}L
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Total P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={cn(
            'text-2xl font-bold',
            stats.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}>
            {stats.total_pnl >= 0 ? '+' : ''}{formatCurrency(stats.total_pnl)}
          </div>
          <p className="text-xs text-muted-foreground">
            {stats.total_trades} total trades
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Avg Win</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">
            +{formatCurrency(stats.avg_win)}
          </div>
          <p className="text-xs text-muted-foreground">
            Best: +{formatCurrency(stats.largest_win)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Avg Loss</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">
            {formatCurrency(stats.avg_loss)}
          </div>
          <p className="text-xs text-muted-foreground">
            Worst: {formatCurrency(stats.largest_loss)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
