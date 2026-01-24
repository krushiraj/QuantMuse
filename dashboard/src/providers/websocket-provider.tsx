'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useWebSocket } from '@/hooks/use-websocket';
import { useSessionStore } from '@/stores/session-store';

interface WebSocketContextValue {
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextValue>({
  isConnected: false,
});

export function useWebSocketContext() {
  return useContext(WebSocketContext);
}

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { selectedSessionId } = useSessionStore();
  const { isConnected } = useWebSocket(selectedSessionId);

  return (
    <WebSocketContext.Provider value={{ isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
}
