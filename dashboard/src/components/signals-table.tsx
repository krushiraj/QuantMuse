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
import { Signal } from '@/lib/api';
import { Check, X } from 'lucide-react';

interface SignalsTableProps {
  signals: Signal[];
  onApprove?: (signal: Signal) => void;
  onReject?: (signal: Signal) => void;
  showActions?: boolean;
}

export function SignalsTable({ signals, onApprove, onReject, showActions = true }: SignalsTableProps) {
  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">Pending</Badge>;
      case 'executed':
        return <Badge variant="default" className="bg-green-100 text-green-700">Executed</Badge>;
      case 'rejected':
        return <Badge variant="secondary" className="bg-red-50 text-red-700">Rejected</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Symbol</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Strategy</TableHead>
          <TableHead className="text-right">Entry</TableHead>
          <TableHead className="text-right">Stop Loss</TableHead>
          <TableHead className="text-right">Take Profit</TableHead>
          <TableHead className="text-right">Confidence</TableHead>
          <TableHead>Status</TableHead>
          {showActions && <TableHead></TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {signals.length === 0 ? (
          <TableRow>
            <TableCell colSpan={showActions ? 10 : 9} className="text-center text-muted-foreground py-8">
              No signals found
            </TableCell>
          </TableRow>
        ) : (
          signals.map((signal) => (
            <TableRow key={signal.id}>
              <TableCell className="text-muted-foreground">
                {formatDate(signal.created_at)}
              </TableCell>
              <TableCell className="font-medium">{signal.symbol}</TableCell>
              <TableCell>
                <Badge variant={signal.signal_type === 'BUY' ? 'default' : 'destructive'}>
                  {signal.signal_type}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{signal.strategy}</TableCell>
              <TableCell className="text-right">{formatCurrency(signal.entry_price)}</TableCell>
              <TableCell className="text-right text-red-600">{formatCurrency(signal.stop_loss)}</TableCell>
              <TableCell className="text-right text-green-600">{formatCurrency(signal.take_profit)}</TableCell>
              <TableCell className="text-right">
                <Badge variant="outline">{(signal.confidence * 100).toFixed(0)}%</Badge>
              </TableCell>
              <TableCell>{getStatusBadge(signal.status)}</TableCell>
              {showActions && signal.status === 'pending' && (
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onApprove?.(signal)}
                      className="text-green-600 hover:text-green-700 hover:bg-green-50"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onReject?.(signal)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              )}
              {showActions && signal.status !== 'pending' && (
                <TableCell></TableCell>
              )}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
