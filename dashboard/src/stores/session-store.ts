import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SessionStore {
  selectedSessionId: number | null;
  setSelectedSessionId: (id: number | null) => void;
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      selectedSessionId: null,
      setSelectedSessionId: (id) => set({ selectedSessionId: id }),
    }),
    {
      name: 'paper-trading-session',
    }
  )
);
