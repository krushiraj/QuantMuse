'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Position } from '@/lib/api';
import { cn } from '@/lib/utils';

interface RecentPositionsProps {
  positions: Position[];
}

export function RecentPositions({ positions }: RecentPositionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {positions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open positions</p>
          ) : (
            positions.slice(0, 5).map((position) => (
              <div
                key={position.id}
                className="flex items-center justify-between"
              >
                <div>
                  <p className="font-medium">{position.symbol}</p>
                  <p className="text-xs text-muted-foreground">
                    {position.quantity} @ ₹{position.entry_price.toFixed(2)}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={cn(
                      'font-medium',
                      position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {position.unrealized_pnl >= 0 ? '+' : ''}₹{position.unrealized_pnl.toFixed(2)}
                  </p>
                  <Badge
                    variant={position.unrealized_pnl_pct >= 0 ? 'default' : 'destructive'}
                    className="text-xs"
                  >
                    {position.unrealized_pnl_pct >= 0 ? '+' : ''}{position.unrealized_pnl_pct.toFixed(2)}%
                  </Badge>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
