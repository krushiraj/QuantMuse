'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MarketStatus } from '@/lib/api';
import { Globe, Clock } from 'lucide-react';

interface MarketStatusCardProps {
  status: MarketStatus;
}

export function MarketStatusCard({ status }: MarketStatusCardProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">NSE India</CardTitle>
          <Globe className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Badge variant={status.nse.is_open ? 'default' : 'secondary'}>
              {status.nse.is_open ? 'Open' : 'Closed'}
            </Badge>
          </div>
          <div className="mt-2 flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="h-3 w-3" />
            {status.nse.hours} ({status.nse.timezone})
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Crypto</CardTitle>
          <Globe className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Badge variant={status.crypto.is_open ? 'default' : 'secondary'}>
              {status.crypto.is_open ? 'Open' : 'Closed'}
            </Badge>
          </div>
          <div className="mt-2 flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="h-3 w-3" />
            {status.crypto.hours}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
