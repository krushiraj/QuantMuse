'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { positionsAPI, Position } from '@/lib/api';
import { useSessionStore } from '@/stores/session-store';
import { PositionsTable } from '@/components/positions-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export default function PositionsPage() {
  const { selectedSessionId } = useSessionStore();
  const queryClient = useQueryClient();
  const [positionToClose, setPositionToClose] = useState<Position | null>(null);
  const [activeTab, setActiveTab] = useState('open');

  const { data: positions, isLoading } = useQuery({
    queryKey: ['positions', selectedSessionId, activeTab === 'all' ? undefined : activeTab],
    queryFn: () => positionsAPI.list(selectedSessionId!, activeTab === 'all' ? undefined : activeTab),
    enabled: !!selectedSessionId,
  });

  const closeMutation = useMutation({
    mutationFn: (position: Position) =>
      positionsAPI.close(position.id, { reason: 'manual', close_price: position.current_price }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['session-summary'] });
      setPositionToClose(null);
    },
  });

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card className="p-8">
          <CardContent className="text-center">
            <h2 className="text-xl font-semibold mb-2">No Session Selected</h2>
            <p className="text-muted-foreground">
              Select a trading session from the dropdown above to view positions.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Positions</h1>
        <p className="text-muted-foreground">Manage your trading positions</p>
      </div>

      <Card>
        <CardHeader>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="open">Open</TabsTrigger>
              <TabsTrigger value="closed">Closed</TabsTrigger>
              <TabsTrigger value="all">All</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <PositionsTable
              positions={positions || []}
              onClose={activeTab === 'open' ? setPositionToClose : undefined}
            />
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!positionToClose} onOpenChange={() => setPositionToClose(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Close Position</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to close your {positionToClose?.symbol} position?
              This will sell {positionToClose?.quantity} shares at the current market price.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => positionToClose && closeMutation.mutate(positionToClose)}
              className="bg-red-600 hover:bg-red-700"
            >
              Close Position
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
