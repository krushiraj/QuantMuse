'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { MarketPrice } from '@/lib/api';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface WatchlistProps {
  title: string;
  prices: MarketPrice[];
  isLoading?: boolean;
}

export function Watchlist({ title, prices, isLoading }: WatchlistProps) {
  const formatCurrency = (value: number, isCrypto: boolean = false) => {
    if (isCrypto) {
      return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const isCrypto = title.toLowerCase().includes('crypto');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : prices.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">No data available</p>
        ) : (
          <div className="space-y-2">
            {prices.map((price) => (
              <div
                key={price.symbol}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div>
                  <p className="font-medium">{price.symbol.replace('.NS', '')}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(price.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatCurrency(price.price, isCrypto)}</p>
                  <div className="flex items-center justify-end gap-1">
                    {price.change_pct >= 0 ? (
                      <TrendingUp className="h-3 w-3 text-green-600" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-red-600" />
                    )}
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs',
                        price.change_pct >= 0 ? 'text-green-600 border-green-200' : 'text-red-600 border-red-200'
                      )}
                    >
                      {price.change_pct >= 0 ? '+' : ''}{price.change_pct.toFixed(2)}%
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
