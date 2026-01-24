'use client';

import { useQuery } from '@tanstack/react-query';
import { marketsAPI } from '@/lib/api';
import { MarketStatusCard } from '@/components/market-status';
import { Watchlist } from '@/components/watchlist';
import { Skeleton } from '@/components/ui/skeleton';

export default function MarketsPage() {
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['market-status'],
    queryFn: marketsAPI.getStatus,
    refetchInterval: 60000, // Refresh every minute
  });

  const { data: watchlist } = useQuery({
    queryKey: ['watchlist'],
    queryFn: marketsAPI.getWatchlist,
  });

  const { data: nsePrices, isLoading: nseLoading } = useQuery({
    queryKey: ['nse-prices', watchlist?.nse],
    queryFn: () => marketsAPI.getPrices(watchlist!.nse),
    enabled: !!watchlist?.nse,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: cryptoPrices, isLoading: cryptoLoading } = useQuery({
    queryKey: ['crypto-prices', watchlist?.crypto],
    queryFn: () => marketsAPI.getPrices(watchlist!.crypto),
    enabled: !!watchlist?.crypto,
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Markets</h1>
        <p className="text-muted-foreground">Market status and watchlist prices</p>
      </div>

      {statusLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[120px]" />
        </div>
      ) : status ? (
        <MarketStatusCard status={status} />
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Watchlist
          title="NSE India Watchlist"
          prices={nsePrices || []}
          isLoading={nseLoading}
        />
        <Watchlist
          title="Crypto Watchlist"
          prices={cryptoPrices || []}
          isLoading={cryptoLoading}
        />
      </div>
    </div>
  );
}
