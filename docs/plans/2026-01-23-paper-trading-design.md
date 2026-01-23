# Paper Trading System Design

**Date:** 2026-01-23
**Status:** Approved
**Branch:** `feature/paper-trading`

---

## 1. Overview

Build a paper trading system for swing trades across multiple markets (Crypto via Binance, NSE India via yfinance). The system will simulate real trading with position management, risk controls, and a full dashboard for monitoring performance.

### Goals
- Paper trade crypto and NSE stocks with realistic execution simulation
- Variable holding periods with signal-driven exits
- Risk-based position sizing with volatility adjustment
- Full dashboard to monitor positions, trades, and performance
- Path to live trading (Zerodha/Angel One integration later)

### Markets

| Market | Data Source | Update Frequency | Status |
|--------|-------------|------------------|--------|
| Crypto | Binance WebSocket | Real-time | Ready |
| NSE India | yfinance (.NS suffix) | 15 min polling | To implement |

**Note:** yfinance has 15-20 min delay. Acceptable for swing trades with wider stops (5%+). Will upgrade to Zerodha/Angel One for live trading.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PAPER TRADING SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Data Layer   │───▶│ Signal Layer │───▶│ Execution    │          │
│  │              │    │              │    │ Layer        │          │
│  │ • Binance WS │    │ • Strategies │    │ • Paper      │          │
│  │ • yfinance   │    │ • Factors    │    │   Executor   │          │
│  │   (.NS)      │    │ • Screeners  │    │ • Position   │          │
│  │              │    │              │    │   Manager    │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             ▼                                       │
│                   ┌──────────────────┐                              │
│                   │  Database Layer  │                              │
│                   │  • Positions     │                              │
│                   │  • Trades        │                              │
│                   │  • Performance   │                              │
│                   └──────────────────┘                              │
│                             │                                       │
│                             ▼                                       │
│                   ┌──────────────────┐                              │
│                   │    Dashboard     │                              │
│                   │  • Portfolio     │                              │
│                   │  • Positions     │                              │
│                   │  • Charts        │                              │
│                   └──────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Position Sizing & Risk Management

### Formula

```
Position Size = (Portfolio Value × Risk Per Trade) / (Entry Price × Stop Distance × Volatility Factor)
```

### Example

- Portfolio: ₹10,00,000
- Risk per trade: 1% (₹10,000)
- Entry: ₹500
- Stop-loss: ₹475 (5% below entry)
- Volatility factor: 1.2 (high volatility asset)

```
Position Size = 10,000 / (500 × 0.05 × 1.2) = 333 shares
Position Value = 333 × 500 = ₹1,66,500 (16.6% of portfolio)
```

### Constraints

| Rule | Value | Purpose |
|------|-------|---------|
| Max risk per trade | 1-2% of portfolio | Limits single-trade loss |
| Max position size | 20% of portfolio | Prevents over-concentration |
| Min position size | ₹5,000 | Avoids tiny positions |
| Max portfolio exposure | 80% | Keeps cash buffer |
| Volatility multiplier | ATR-based | Scales down for volatile assets |

### Volatility Factor Calculation

```
Asset ATR% = (14-day ATR / Current Price) × 100
Baseline ATR% = 2% (configurable)
Volatility Factor = Asset ATR% / Baseline ATR%

If BTC ATR% = 4%, factor = 4/2 = 2.0 → position halved
If RELIANCE ATR% = 1.5%, factor = 1.5/2 = 0.75 → position increased
```

---

## 4. Exit Management

### Exit Rules (whichever triggers first)

| Condition | Action | Example |
|-----------|--------|---------|
| Price ≤ Hard stop-loss | Exit immediately | Price hits -5% → sell |
| Price ≤ Trailing stop | Exit immediately | Price drops 3% from high → sell |
| Price ≥ Take-profit target | Exit immediately | Price hits +15% → sell |
| Signal reversal | Optional exit | Strategy signals SELL → close |
| Confidence drops below threshold | Exit or partial close | See Section 5 |

### Trailing Stop Logic

```
Entry: ₹500    Hard SL: ₹475 (-5%)    TP Target: ₹575 (+15%)

Price moves to ₹540 (+8%)
├── Trailing stop activates at +5% profit
└── Trail distance: 3% below high
    New trailing stop: ₹540 × 0.97 = ₹523.80

Price moves to ₹560 (+12%)
└── Trailing stop updates: ₹560 × 0.97 = ₹543.20

Price drops to ₹543 → EXIT (trailing stop hit)
Profit locked: (₹543 - ₹500) / ₹500 = +8.6%
```

### Exit Configuration

```python
exit_config = {
    "hard_stop_loss_pct": 5.0,
    "take_profit_pct": 15.0,
    "trailing_stop_activation": 5.0,
    "trailing_stop_distance": 3.0,
    "use_atr_stops": True,
    "atr_stop_multiplier": 2.0,
}
```

---

## 5. Dynamic Position Management (Confidence-Based)

### Confidence Tiers

| Confidence Level | Action | SL Adjust | TP Adjust |
|------------------|--------|-----------|-----------|
| 0.80 - 1.00 | Hold, original params | 100% | 100% |
| 0.60 - 0.79 | Tighten stops | 80% | 70% |
| 0.40 - 0.59 | Partial close (50%) + tighten | 60% | 50% |
| 0.20 - 0.39 | Close position | Exit | Exit |
| < 0.20 | Immediate exit | Exit | Exit |

### Example Flow

```
ENTRY (confidence: 0.85)
├── SL: -5%  TP: +15%  Trail: 3%

POLL 1: confidence drops to 0.70
├── Action: Tighten stops
├── New SL: -4%  New TP: +10%  Trail: 2.5%

POLL 2: confidence drops to 0.50
├── Action: Tighten further + partial close
├── Close 50% of position, lock partial profit
├── Remaining: SL: -3%  TP: +7%

POLL 3: confidence drops to 0.30
└── Action: Close entire position (confidence too low)
```

### Re-evaluation Triggers

| Trigger | Action |
|---------|--------|
| Scheduled poll (15 min NSE, real-time crypto) | Recalculate signal strength |
| Major price move (>2% since last check) | Immediate re-evaluation |
| News event (sentiment spike) | Re-run sentiment factors |
| Strategy signal flips to SELL | Consider early exit |

---

## 6. Signal Generation

### Signal Pipeline

```
Fetch Data → Calculate Factors → Run Strategies → Generate Trade Signal
```

### Signal Structure

```python
signal = {
    "symbol": "RELIANCE.NS",
    "market": "nse",
    "direction": "BUY",
    "entry_price": 2450.00,
    "stop_loss": 2327.50,
    "take_profit": 2817.50,
    "trailing_activation": 2572.50,
    "signal_strength": 0.85,
    "strategy": "MultiFactorStrategy",
    "factors": {
        "momentum_60d": 12.5,
        "rsi": 42,
        "pe_ratio": 22.3,
    },
    "timestamp": "2026-01-23T10:30:00",
}
```

### Execution Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| Auto | Execute immediately if passes risk checks | Hands-off paper testing |
| Review | Queue for manual approval | Learning, building confidence |
| Hybrid | Auto for high-strength (>0.8), review for others | Balanced approach |

### Polling Schedule

| Market | Data Source | Frequency | Hours |
|--------|-------------|-----------|-------|
| Crypto | Binance WebSocket | Real-time | 24/7 |
| NSE | yfinance | Every 15 min | 9:15 AM - 3:30 PM IST |

---

## 7. Database Schema

```
┌──────────────────────┐       ┌──────────────────────┐
│   paper_sessions     │       │   paper_positions    │
├──────────────────────┤       ├──────────────────────┤
│ id (PK)              │       │ id (PK)              │
│ name                 │       │ session_id (FK)      │
│ initial_balance      │──────▶│ symbol               │
│ current_balance      │       │ market (nse/crypto)  │
│ start_date           │       │ direction (long)     │
│ status (active/ended)│       │ quantity             │
│ config_json          │       │ entry_price          │
│ created_at           │       │ current_price        │
└──────────────────────┘       │ stop_loss            │
                               │ take_profit          │
                               │ trailing_stop        │
                               │ entry_confidence     │
                               │ current_confidence   │
                               │ strategy             │
                               │ status (open/closed) │
                               │ opened_at            │
                               │ closed_at            │
                               │ close_reason         │
                               └──────────────────────┘

┌──────────────────────┐       ┌──────────────────────┐
│   paper_trades       │       │ position_adjustments │
├──────────────────────┤       ├──────────────────────┤
│ id (PK)              │       │ id (PK)              │
│ session_id (FK)      │       │ position_id (FK)     │
│ position_id (FK)     │       │ adjustment_type      │
│ symbol               │       │ old_sl / new_sl      │
│ trade_type           │       │ old_tp / new_tp      │
│ quantity             │       │ old_confidence       │
│ price                │       │ new_confidence       │
│ value                │       │ reason               │
│ commission           │       │ timestamp            │
│ pnl (for exits)      │       └──────────────────────┘
│ timestamp            │
└──────────────────────┘
                               ┌──────────────────────┐
┌──────────────────────┐       │   pending_signals    │
│  performance_daily   │       ├──────────────────────┤
├──────────────────────┤       │ id (PK)              │
│ id (PK)              │       │ session_id (FK)      │
│ session_id (FK)      │       │ symbol               │
│ date                 │       │ market               │
│ portfolio_value      │       │ signal_type (BUY)    │
│ cash_balance         │       │ entry_price          │
│ invested_value       │       │ stop_loss            │
│ daily_pnl            │       │ take_profit          │
│ daily_return_pct     │       │ confidence           │
│ cumulative_return    │       │ strategy             │
│ drawdown             │       │ factors_json         │
│ num_positions        │       │ status (pending/     │
│ num_trades           │       │   executed/rejected) │
└──────────────────────┘       │ created_at           │
                               │ reviewed_at          │
                               └──────────────────────┘
```

---

## 8. Dashboard

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI (Python) |
| Frontend | Next.js 14 (App Router) |
| UI Components | shadcn/ui + Tailwind CSS |
| Charts | Recharts |
| State Management | React Query (TanStack Query) |
| Real-time | WebSocket client |
| Database | SQLite (dev) → PostgreSQL (prod) |

### Pages

1. **Portfolio Overview** - Total value, P&L, cash, exposure, win rate, mini equity curve
2. **Open Positions** - Sortable table with entry, current, P&L, SL/TP, confidence, close button
3. **Trade History** - Closed trades, realized P&L, close reason, filters
4. **Pending Signals** - Review mode queue with approve/reject buttons
5. **Performance Analytics** - Equity curve, drawdown, monthly returns, metrics
6. **Market Overview** - Watchlist, top movers, market status

### API Endpoints

```
GET    /api/sessions                 # List sessions
POST   /api/sessions                 # Create session
GET    /api/sessions/{id}            # Session details

GET    /api/positions                # Open positions
POST   /api/positions/{id}/close     # Manual close
GET    /api/positions/{id}/history   # Adjustment history

GET    /api/trades                   # Trade history
GET    /api/trades/stats             # Win rate, avg P&L, etc.

GET    /api/signals                  # Pending signals
POST   /api/signals/{id}/approve     # Execute signal
POST   /api/signals/{id}/reject      # Reject signal

GET    /api/performance/daily        # Daily snapshots
GET    /api/performance/metrics      # Sharpe, drawdown, etc.

GET    /api/markets/prices           # Current prices
WS     /api/ws                       # Real-time updates
```

---

## 9. Project Structure

```
QuantMuse/
├── data_service/                    # Existing Python code
│   ├── fetchers/
│   │   ├── nse_fetcher.py           # NEW: yfinance NSE integration
│   │   └── ...
│   ├── factors/
│   ├── strategies/
│   └── ...
│
├── paper_trading/                   # NEW: Paper trading engine
│   ├── __init__.py
│   ├── engine.py                    # Main paper trading loop
│   ├── position_manager.py          # Position sizing & risk
│   ├── exit_manager.py              # SL/TP/Trailing logic
│   ├── confidence_monitor.py        # Dynamic adjustments
│   ├── executor.py                  # Paper trade execution
│   ├── models.py                    # SQLAlchemy models
│   └── config.py                    # Configuration
│
├── api/                             # NEW: FastAPI backend
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   │   ├── sessions.py
│   │   ├── positions.py
│   │   ├── trades.py
│   │   ├── signals.py
│   │   ├── performance.py
│   │   └── markets.py
│   ├── schemas.py
│   └── websocket.py
│
├── dashboard/                       # NEW: Next.js frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── positions/
│   │   ├── trades/
│   │   ├── signals/
│   │   ├── performance/
│   │   └── markets/
│   ├── components/
│   │   ├── ui/                      # shadcn components
│   │   ├── portfolio-card.tsx
│   │   ├── positions-table.tsx
│   │   ├── equity-chart.tsx
│   │   └── confidence-badge.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── package.json
│   └── tailwind.config.js
│
├── scripts/
│   ├── run_paper_trading.py
│   └── run_api_server.py
│
└── docs/
    └── plans/
        └── 2026-01-23-paper-trading-design.md
```

---

## 10. Configuration

```python
class PaperTradingConfig:

    # === SESSION ===
    session = {
        "initial_balance": 1000000,
        "currency": "INR",
        "execution_mode": "auto",
        "hybrid_confidence_threshold": 0.80,
    }

    # === MARKETS ===
    markets = {
        "nse": {
            "enabled": True,
            "data_source": "yfinance",
            "poll_interval_minutes": 15,
            "market_open": "09:15",
            "market_close": "15:30",
            "timezone": "Asia/Kolkata",
            "commission_pct": 0.02,
            "watchlist": [
                "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS",
                "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
                "KOTAKBANK.NS", "ITC.NS", "SBIN.NS"
            ],
        },
        "crypto": {
            "enabled": True,
            "data_source": "binance",
            "use_websocket": True,
            "commission_pct": 0.1,
            "watchlist": [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"
            ],
        },
    }

    # === POSITION SIZING ===
    sizing = {
        "risk_per_trade_pct": 1.0,
        "max_position_pct": 20.0,
        "min_position_value": 5000,
        "max_portfolio_exposure_pct": 80.0,
        "use_volatility_adjustment": True,
        "baseline_atr_pct": 2.0,
    }

    # === EXIT RULES ===
    exits = {
        "default_stop_loss_pct": 5.0,
        "default_take_profit_pct": 15.0,
        "trailing_stop_activation_pct": 5.0,
        "trailing_stop_distance_pct": 3.0,
        "use_atr_stops": True,
        "atr_stop_multiplier": 2.0,
        "atr_tp_multiplier": 3.0,
    }

    # === CONFIDENCE MANAGEMENT ===
    confidence = {
        "enable_dynamic_management": True,
        "recalc_interval_minutes": 15,
        "tiers": [
            {"min": 0.80, "sl_factor": 1.0, "tp_factor": 1.0, "action": "hold"},
            {"min": 0.60, "sl_factor": 0.8, "tp_factor": 0.7, "action": "tighten"},
            {"min": 0.40, "sl_factor": 0.6, "tp_factor": 0.5, "action": "partial_close"},
            {"min": 0.00, "sl_factor": 0.0, "tp_factor": 0.0, "action": "close"},
        ],
        "partial_close_pct": 50,
        "min_hold_time_minutes": 30,
    }

    # === STRATEGIES ===
    strategies = {
        "enabled": ["MultiFactorStrategy", "MomentumStrategy"],
        "ensemble_method": "equal_weight",
        "min_signal_confidence": 0.60,
    }

    # === DATABASE ===
    database = {
        "url": "sqlite:///paper_trading.db",
    }

    # === DASHBOARD ===
    dashboard = {
        "api_port": 8000,
        "frontend_port": 3000,
        "refresh_interval_seconds": 30,
        "websocket_enabled": True,
    }
```

---

## 11. Implementation Phases

### Phase 1: Core Engine

| Task | Files | Priority |
|------|-------|----------|
| SQLAlchemy models | `paper_trading/models.py` | P0 |
| Config loader | `paper_trading/config.py` | P0 |
| Position manager | `paper_trading/position_manager.py` | P0 |
| Exit manager | `paper_trading/exit_manager.py` | P0 |
| Paper executor | `paper_trading/executor.py` | P0 |
| NSE fetcher | `data_service/fetchers/nse_fetcher.py` | P0 |
| Engine loop | `paper_trading/engine.py` | P0 |
| CLI runner | `scripts/run_paper_trading.py` | P1 |

**Deliverable:** Can run paper trades via CLI

### Phase 2: API Layer

| Task | Files | Priority |
|------|-------|----------|
| FastAPI app setup | `api/main.py` | P0 |
| Session router | `api/routers/sessions.py` | P0 |
| Positions router | `api/routers/positions.py` | P0 |
| Trades router | `api/routers/trades.py` | P0 |
| Performance router | `api/routers/performance.py` | P1 |
| Markets router | `api/routers/markets.py` | P1 |
| WebSocket handler | `api/websocket.py` | P1 |
| Pydantic schemas | `api/schemas.py` | P0 |

**Deliverable:** Full REST API + WebSocket

### Phase 3: Dashboard

| Task | Files | Priority |
|------|-------|----------|
| Next.js + shadcn setup | `dashboard/*` | P0 |
| Layout & navigation | `app/layout.tsx` | P0 |
| Portfolio overview | `app/page.tsx` | P0 |
| Positions page | `app/positions/page.tsx` | P0 |
| Trades page | `app/trades/page.tsx` | P1 |
| Performance page | `app/performance/page.tsx` | P1 |
| Signals page | `app/signals/page.tsx` | P1 |
| Markets page | `app/markets/page.tsx` | P2 |
| WebSocket hook | `lib/websocket.ts` | P1 |

**Deliverable:** Fully functional dashboard

### Phase 4: Advanced Features

| Task | Priority |
|------|----------|
| Confidence monitoring & dynamic adjustments | P1 |
| Crypto real-time via Binance WebSocket | P1 |
| Strategy ensemble execution | P2 |
| Sentiment factor integration | P2 |
| Alerts & notifications | P2 |

**Deliverable:** Production-ready paper trading

---

## 12. Future: Live Trading Integration

Once paper trading proves successful:

1. **Zerodha Kite API** or **Angel One API** for NSE order execution
2. **Binance Order API** for crypto execution
3. **Paper → Live toggle** in configuration
4. Same dashboard, same strategies, real money

---

## Appendix: Decision Log

| Decision | Rationale |
|----------|-----------|
| yfinance for NSE | Free, proven in trade-ml, upgrade later |
| Variable holding period | Swing trade style, exit on signals not time |
| Trailing + hard stop | Lock profits while limiting downside |
| Risk-based + vol-adjusted sizing | Consistent risk, adapt to asset volatility |
| Dynamic position count | Maximum flexibility with exposure cap |
| Confidence-based adjustments | Reduce exposure when signal weakens |
| Next.js + shadcn | Modern stack, fast development, good UX |
| SQLite for dev | Simple, no setup, PostgreSQL for prod |
