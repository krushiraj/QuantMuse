'use client';

import { useQuery } from '@tanstack/react-query';
import { sessionsAPI, Session } from '@/lib/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSessionStore } from '@/stores/session-store';
import { ConnectionStatus } from '@/components/connection-status';

export function Header() {
  const { selectedSessionId, setSelectedSessionId } = useSessionStore();

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: sessionsAPI.list,
  });

  return (
    <header className="border-b bg-card px-6 py-4 flex items-center justify-between">
      <div>
        <h2 className="text-lg font-semibold">Dashboard</h2>
      </div>
      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Session:</span>
          <Select
            value={selectedSessionId?.toString() || ''}
            onValueChange={(value) => setSelectedSessionId(Number(value))}
            disabled={isLoading}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select session" />
            </SelectTrigger>
            <SelectContent>
              {sessions?.map((session: Session) => (
                <SelectItem key={session.id} value={session.id.toString()}>
                  {session.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </header>
  );
}
