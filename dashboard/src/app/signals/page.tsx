'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { signalsAPI, Signal } from '@/lib/api';
import { useSessionStore } from '@/stores/session-store';
import { SignalsTable } from '@/components/signals-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

export default function SignalsPage() {
  const { selectedSessionId } = useSessionStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('pending');

  const { data: signals, isLoading } = useQuery({
    queryKey: ['signals', selectedSessionId, activeTab === 'all' ? undefined : activeTab],
    queryFn: () => signalsAPI.list(selectedSessionId!, activeTab === 'all' ? undefined : activeTab),
    enabled: !!selectedSessionId,
  });

  const { data: pendingSignals } = useQuery({
    queryKey: ['signals', selectedSessionId, 'pending'],
    queryFn: () => signalsAPI.list(selectedSessionId!, 'pending'),
    enabled: !!selectedSessionId,
  });

  const approveMutation = useMutation({
    mutationFn: (signal: Signal) => signalsAPI.action(signal.id, 'approve'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['session-summary'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (signal: Signal) => signalsAPI.action(signal.id, 'reject'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    },
  });

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Card className="p-8">
          <CardContent className="text-center">
            <h2 className="text-xl font-semibold mb-2">No Session Selected</h2>
            <p className="text-muted-foreground">
              Select a trading session from the dropdown above to view signals.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const pendingCount = pendingSignals?.length || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trading Signals</h1>
          <p className="text-muted-foreground">Review and manage trading signals</p>
        </div>
        {pendingCount > 0 && (
          <Badge variant="destructive" className="text-lg px-3 py-1">
            {pendingCount} Pending
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="pending" className="relative">
                Pending
                {pendingCount > 0 && (
                  <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                    {pendingCount}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="executed">Executed</TabsTrigger>
              <TabsTrigger value="rejected">Rejected</TabsTrigger>
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
            <SignalsTable
              signals={signals || []}
              onApprove={(signal) => approveMutation.mutate(signal)}
              onReject={(signal) => rejectMutation.mutate(signal)}
              showActions={activeTab === 'pending' || activeTab === 'all'}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
