'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Trade } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TradesTableProps {
  trades: Trade[];
}

export function TradesTable({ trades }: TradesTableProps) {
  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Symbol</TableHead>
          <TableHead>Type</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead className="text-right">Commission</TableHead>
          <TableHead className="text-right">P&L</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.length === 0 ? (
          <TableRow>
            <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
              No trades found
            </TableCell>
          </TableRow>
        ) : (
          trades.map((trade) => (
            <TableRow key={trade.id}>
              <TableCell className="text-muted-foreground">
                {formatDate(trade.timestamp)}
              </TableCell>
              <TableCell className="font-medium">{trade.symbol}</TableCell>
              <TableCell>
                <Badge variant={trade.trade_type === 'buy' ? 'default' : 'secondary'}>
                  {trade.trade_type.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-right">{trade.quantity}</TableCell>
              <TableCell className="text-right">{formatCurrency(trade.price)}</TableCell>
              <TableCell className="text-right">{formatCurrency(trade.value)}</TableCell>
              <TableCell className="text-right text-muted-foreground">
                {formatCurrency(trade.commission)}
              </TableCell>
              <TableCell className="text-right">
                {trade.pnl !== null ? (
                  <span className={cn(
                    'font-medium',
                    trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  )}>
                    {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
