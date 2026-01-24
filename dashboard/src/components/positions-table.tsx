'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Position } from '@/lib/api';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface PositionsTableProps {
  positions: Position[];
  onClose?: (position: Position) => void;
}

export function PositionsTable({ positions, onClose }: PositionsTableProps) {
  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Market</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Entry</TableHead>
          <TableHead className="text-right">Current</TableHead>
          <TableHead className="text-right">Stop Loss</TableHead>
          <TableHead className="text-right">Take Profit</TableHead>
          <TableHead className="text-right">P&L</TableHead>
          <TableHead className="text-right">P&L %</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.length === 0 ? (
          <TableRow>
            <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
              No positions found
            </TableCell>
          </TableRow>
        ) : (
          positions.map((position) => (
            <TableRow key={position.id}>
              <TableCell className="font-medium">{position.symbol}</TableCell>
              <TableCell>
                <Badge variant="outline">{position.market.toUpperCase()}</Badge>
              </TableCell>
              <TableCell className="text-right">{position.quantity}</TableCell>
              <TableCell className="text-right">{formatCurrency(position.entry_price)}</TableCell>
              <TableCell className="text-right">{formatCurrency(position.current_price)}</TableCell>
              <TableCell className="text-right text-red-600">{formatCurrency(position.stop_loss)}</TableCell>
              <TableCell className="text-right text-green-600">{formatCurrency(position.take_profit)}</TableCell>
              <TableCell
                className={cn(
                  'text-right font-medium',
                  position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                )}
              >
                {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
              </TableCell>
              <TableCell className="text-right">
                <Badge variant={position.unrealized_pnl_pct >= 0 ? 'default' : 'destructive'}>
                  {formatPercent(position.unrealized_pnl_pct)}
                </Badge>
              </TableCell>
              <TableCell>
                {position.status === 'open' && onClose && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onClose(position)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
