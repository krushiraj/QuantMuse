# Paper Trading System Guide

A comprehensive paper trading system for simulating trades with real market data without risking actual capital.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Dashboard](#dashboard)
- [Advanced Features](#advanced-features)

## Overview

The paper trading system provides:

- **Simulated Trading**: Execute trades with virtual capital using real market prices
- **Risk Management**: Position sizing, stop-loss, take-profit, and trailing stops
- **Confidence-Based Management**: Dynamic position adjustments based on signal confidence
- **Real-time Data**: Live crypto prices via Binance WebSocket
- **Performance Analytics**: Sharpe ratio, Sortino ratio, drawdown analysis
- **Alert System**: Notifications for trades, signals, and stop-loss hits
- **Web Dashboard**: Real-time monitoring with Next.js + shadcn/ui

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Dashboard (Next.js 14)                       │
│  • Portfolio Overview    • Positions    • Trades    • Signals   │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                         │
│  • Sessions    • Positions    • Trades    • Signals    • Alerts │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Paper Trading Engine                           │
├─────────────────────────────────────────────────────────────────┤
│  Position Manager  │  Exit Manager  │  Confidence Monitor       │
│  Trade Executor    │  Risk Sizer    │  Performance Tracker      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                  │
│  • Binance WebSocket (Crypto)    • yfinance (NSE Stocks)        │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start the API Server

```bash
cd /path/to/QuantMuse

# Initialize database and start server
python -c "from paper_trading.models import Base, engine; Base.metadata.create_all(engine)"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
# Visit http://localhost:3000
```

### 3. Create a Trading Session

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Paper Trading Session",
    "initial_balance": 1000000,
    "config": {
      "execution_mode": "auto"
    }
  }'
```

### 4. Create a Signal

```bash
curl -X POST http://localhost:8000/api/signals \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "symbol": "BTCUSDT",
    "market": "crypto",
    "signal_type": "buy",
    "entry_price": 42000,
    "stop_loss": 40000,
    "take_profit": 48000,
    "confidence": 0.85
  }'
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for dashboard)
- SQLite (default) or PostgreSQL

### Python Dependencies

```bash
# Install paper trading module
pip install -e .

# Or install specific dependencies
pip install sqlalchemy fastapi uvicorn websockets apscheduler
```

### Dashboard Dependencies

```bash
cd dashboard
npm install
```

## Configuration

### Session Configuration

```python
from paper_trading.config import PaperTradingConfig, SessionConfig

config = PaperTradingConfig(
    session=SessionConfig(
        initial_balance=1000000.0,
        currency="INR",
        execution_mode="auto",  # auto | review | hybrid
        hybrid_confidence_threshold=0.80
    )
)
```

### Position Sizing

```python
from paper_trading.config import SizingConfig

sizing = SizingConfig(
    risk_per_trade_pct=1.0,       # Risk 1% per trade
    max_position_pct=20.0,        # Max 20% in single position
    min_position_value=5000.0,    # Min position size
    max_portfolio_exposure_pct=80.0,
    use_volatility_adjustment=True,
    baseline_atr_pct=2.0
)
```

### Exit Rules

```python
from paper_trading.config import ExitConfig

exits = ExitConfig(
    default_stop_loss_pct=5.0,
    default_take_profit_pct=15.0,
    trailing_stop_activation_pct=5.0,
    trailing_stop_distance_pct=3.0,
    use_atr_stops=True,
    atr_stop_multiplier=2.0,
    atr_tp_multiplier=3.0
)
```

### Market Configuration

```python
from paper_trading.config import MarketConfig

nse_config = MarketConfig(
    enabled=True,
    data_source="yfinance",
    poll_interval_minutes=15,
    market_open="09:15",
    market_close="15:30",
    timezone="Asia/Kolkata",
    commission_pct=0.02,
    watchlist=["RELIANCE.NS", "TCS.NS", "INFY.NS"]
)

crypto_config = MarketConfig(
    enabled=True,
    data_source="binance",
    poll_interval_minutes=1,
    commission_pct=0.1,
    watchlist=["BTCUSDT", "ETHUSDT", "SOLUSDT"]
)
```

## API Reference

### Sessions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/{id}` | GET | Get session details |
| `/api/sessions/{id}/portfolio` | GET | Get portfolio summary |

### Positions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/positions` | GET | List positions (filter by session_id, status) |
| `/api/positions/{id}` | GET | Get position details |
| `/api/positions/{id}/close` | POST | Manually close position |
| `/api/positions/{id}/history` | GET | Get position adjustment history |

### Trades

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trades` | GET | List trades (filter by session_id, symbol) |
| `/api/trades/stats` | GET | Get trade statistics |

### Signals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/signals` | GET | List pending signals |
| `/api/signals` | POST | Create new signal |
| `/api/signals/{id}/approve` | POST | Approve and execute signal |
| `/api/signals/{id}/reject` | POST | Reject signal |

### Markets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/markets/prices` | GET | Get current prices for watchlist |
| `/api/markets/status` | GET | Get market open/closed status |

### Performance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/performance/{session_id}` | GET | Get performance metrics |
| `/api/performance/{session_id}/equity` | GET | Get equity curve data |
| `/api/performance/{session_id}/drawdown` | GET | Get drawdown history |

### Alerts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET | List alerts |
| `/api/alerts/{id}/read` | POST | Mark alert as read |

### WebSocket

```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data.type, data.payload);
};

// Message types: price_update, position_update, trade_executed, alert
```

## Dashboard

The Next.js dashboard provides:

### Portfolio Overview (/)
- Total portfolio value
- Cash balance and invested value
- Daily P&L and return percentage
- Mini equity curve chart

### Positions (/positions)
- Open and closed positions
- Real-time P&L updates
- Stop-loss and take-profit levels
- Manual close functionality

### Trades (/trades)
- Complete trade history
- Win rate and average P&L
- Filter by symbol and date

### Signals (/signals)
- Pending signals for review
- Signal details with confidence score
- Approve/reject actions

### Performance (/performance)
- Equity curve chart
- Drawdown visualization
- Performance metrics (Sharpe, Sortino, Calmar)
- Monthly returns heatmap

### Markets (/markets)
- Watchlist with live prices
- Market status indicator
- Price change percentages

## Advanced Features

### Confidence-Based Management

The system automatically adjusts positions based on confidence levels:

| Confidence | Action | SL Factor | TP Factor |
|------------|--------|-----------|-----------|
| >= 80% | Hold | 1.0x | 1.0x |
| >= 60% | Tighten stops | 0.8x | 0.7x |
| >= 40% | Partial close (50%) | 0.6x | 0.5x |
| < 40% | Close position | - | - |

### Background Scheduler

Run automated tasks with the scheduler:

```bash
python scripts/run_scheduler.py
```

Scheduled tasks:
- Price updates every minute (crypto) / 15 minutes (stocks)
- Exit checks every 5 minutes
- Confidence recalculation every 15 minutes
- Daily performance snapshots at market close

### Real-time Crypto Prices

```python
from data_service.fetchers.binance_websocket import BinanceWebSocket

async def price_handler(symbol: str, price: float):
    print(f"{symbol}: ${price:,.2f}")

ws = BinanceWebSocket()
await ws.subscribe(["BTCUSDT", "ETHUSDT"], price_handler)
await ws.start()
```

### Strategy Integration

Connect strategies to generate signals:

```python
from paper_trading.strategy_runner import StrategyRunner
from paper_trading.signal_generator import SignalGenerator

runner = StrategyRunner(db_session)
runner.register_strategy("momentum", MomentumStrategy())

# Run strategy and generate signals
signals = runner.run_strategy("momentum", market_data)
signal_gen = SignalGenerator(session_id=1)

for signal in signals:
    trading_signal = signal_gen.generate_from_strategy_output(signal)
    # Signal is created in pending state for review
```

## Troubleshooting

### Database Issues

```bash
# Reset database
rm paper_trading.db
python -c "from paper_trading.models import Base, engine; Base.metadata.create_all(engine)"
```

### API Server Not Starting

Check if port 8000 is available:
```bash
lsof -i :8000
# Kill existing process if needed
kill -9 <PID>
```

### Dashboard Build Errors

```bash
cd dashboard
rm -rf node_modules .next
npm install
npm run dev
```

### WebSocket Connection Issues

Ensure CORS is configured in the API:
```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

```bash
# Run all paper trading tests
python -m pytest tests/test_paper_trading.py tests/test_exit_manager.py -v

# Run with coverage
python -m pytest tests/ --cov=paper_trading --cov-report=html
```

## License

MIT License - See [LICENSE](../LICENSE) for details.
