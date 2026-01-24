# Paper Trading Phase 3: Dashboard Implementation Plan

**Goal:** Build a Next.js 14 dashboard with shadcn/ui for monitoring paper trading sessions.

**Tech Stack:** Next.js 14 (App Router), shadcn/ui, Tailwind CSS, TanStack Query, Recharts

**Branch:** `feature/paper-trading` (continue from Phase 2)

---

## Task 1: Next.js + shadcn/ui Setup

**Commands:**
```bash
cd /Users/krushi/Documents/github/QuantMuse
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd dashboard
npx shadcn@latest init
npx shadcn@latest add button card table badge tabs skeleton
npm install @tanstack/react-query recharts lucide-react
```

**Files to create:**
- `dashboard/src/lib/api.ts` - API client
- `dashboard/src/lib/types.ts` - TypeScript types
- `dashboard/src/providers/query-provider.tsx` - React Query provider

---

## Task 2: Layout & Navigation

**Files:**
- `dashboard/src/app/layout.tsx` - Root layout with sidebar
- `dashboard/src/components/sidebar.tsx` - Navigation sidebar
- `dashboard/src/components/header.tsx` - Top header with session selector

---

## Task 3: Portfolio Overview (Home Page)

**Files:**
- `dashboard/src/app/page.tsx` - Portfolio overview
- `dashboard/src/components/portfolio-card.tsx` - Summary stats card
- `dashboard/src/components/mini-equity-chart.tsx` - Small equity curve

---

## Task 4: Positions Page

**Files:**
- `dashboard/src/app/positions/page.tsx` - Positions list
- `dashboard/src/components/positions-table.tsx` - Sortable positions table
- `dashboard/src/components/position-row.tsx` - Position row with P&L colors

---

## Task 5: Trades Page

**Files:**
- `dashboard/src/app/trades/page.tsx` - Trade history
- `dashboard/src/components/trades-table.tsx` - Trades table with filters
- `dashboard/src/components/trade-stats-card.tsx` - Win rate, avg P&L stats

---

## Task 6: Signals Page

**Files:**
- `dashboard/src/app/signals/page.tsx` - Pending signals
- `dashboard/src/components/signals-table.tsx` - Signals with approve/reject
- `dashboard/src/components/signal-card.tsx` - Signal detail card

---

## Task 7: Performance Page

**Files:**
- `dashboard/src/app/performance/page.tsx` - Analytics
- `dashboard/src/components/equity-chart.tsx` - Full equity curve
- `dashboard/src/components/metrics-grid.tsx` - Performance metrics
- `dashboard/src/components/drawdown-chart.tsx` - Drawdown visualization

---

## Task 8: Markets Page

**Files:**
- `dashboard/src/app/markets/page.tsx` - Market overview
- `dashboard/src/components/watchlist.tsx` - Watchlist with prices
- `dashboard/src/components/market-status.tsx` - Market open/closed status

---

## Task 9: WebSocket Integration

**Files:**
- `dashboard/src/hooks/use-websocket.ts` - WebSocket hook
- `dashboard/src/providers/websocket-provider.tsx` - WebSocket context

---

## Task 10: Final Polish & Testing

- Test all pages
- Verify API integration
- Add loading states
- Add error handling
