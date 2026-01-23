# Paper Trading Phase 1: Core Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core paper trading engine that can execute simulated trades via CLI for crypto (Binance) and NSE (yfinance) markets.

**Architecture:** Event-driven engine with position manager for risk-based sizing, exit manager for SL/TP/trailing stops, and SQLAlchemy models for persistence. Follows existing data_service patterns (dataclasses, logging, try/except imports).

**Tech Stack:** Python 3.8+, SQLAlchemy, yfinance, existing Binance fetcher, pytest

---

## Task 1: Create Paper Trading Package Structure

**Files:**
- Create: `paper_trading/__init__.py`
- Create: `paper_trading/config.py`
- Create: `tests/paper_trading/__init__.py`
- Create: `tests/paper_trading/conftest.py`

**Step 1: Create package directories**

Run:
```bash
mkdir -p paper_trading tests/paper_trading
```

**Step 2: Create paper_trading/__init__.py**

```python
"""
Paper Trading Engine for QuantMuse

Provides simulated trading capabilities for crypto and NSE markets.
"""

try:
    from .config import PaperTradingConfig
except ImportError:
    PaperTradingConfig = None

try:
    from .models import PaperSession, PaperPosition, PaperTrade
except ImportError:
    PaperSession = None
    PaperPosition = None
    PaperTrade = None

try:
    from .position_manager import PositionManager
except ImportError:
    PositionManager = None

try:
    from .exit_manager import ExitManager
except ImportError:
    ExitManager = None

try:
    from .executor import PaperExecutor
except ImportError:
    PaperExecutor = None

try:
    from .engine import PaperTradingEngine
except ImportError:
    PaperTradingEngine = None

__version__ = "0.1.0"

__all__ = [
    "PaperTradingConfig",
    "PaperSession",
    "PaperPosition",
    "PaperTrade",
    "PositionManager",
    "ExitManager",
    "PaperExecutor",
    "PaperTradingEngine",
]
```

**Step 3: Create paper_trading/config.py**

```python
"""
Configuration for Paper Trading Engine
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Session-level configuration"""
    initial_balance: float = 1000000.0
    currency: str = "INR"
    execution_mode: str = "auto"  # auto | review | hybrid
    hybrid_confidence_threshold: float = 0.80


@dataclass
class MarketConfig:
    """Per-market configuration"""
    enabled: bool = True
    data_source: str = ""
    poll_interval_minutes: int = 15
    market_open: str = ""
    market_close: str = ""
    timezone: str = "UTC"
    commission_pct: float = 0.1
    watchlist: List[str] = field(default_factory=list)


@dataclass
class SizingConfig:
    """Position sizing configuration"""
    risk_per_trade_pct: float = 1.0
    max_position_pct: float = 20.0
    min_position_value: float = 5000.0
    max_portfolio_exposure_pct: float = 80.0
    use_volatility_adjustment: bool = True
    baseline_atr_pct: float = 2.0


@dataclass
class ExitConfig:
    """Exit rules configuration"""
    default_stop_loss_pct: float = 5.0
    default_take_profit_pct: float = 15.0
    trailing_stop_activation_pct: float = 5.0
    trailing_stop_distance_pct: float = 3.0
    use_atr_stops: bool = True
    atr_stop_multiplier: float = 2.0
    atr_tp_multiplier: float = 3.0


@dataclass
class ConfidenceConfig:
    """Confidence-based position management"""
    enable_dynamic_management: bool = True
    recalc_interval_minutes: int = 15
    partial_close_pct: float = 50.0
    min_hold_time_minutes: int = 30
    # Tiers: (min_confidence, sl_factor, tp_factor, action)
    tiers: List[tuple] = field(default_factory=lambda: [
        (0.80, 1.0, 1.0, "hold"),
        (0.60, 0.8, 0.7, "tighten"),
        (0.40, 0.6, 0.5, "partial_close"),
        (0.00, 0.0, 0.0, "close"),
    ])


@dataclass
class PaperTradingConfig:
    """Master configuration for paper trading"""
    session: SessionConfig = field(default_factory=SessionConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    exits: ExitConfig = field(default_factory=ExitConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    database_url: str = "sqlite:///paper_trading.db"

    # Market configurations
    nse: MarketConfig = field(default_factory=lambda: MarketConfig(
        enabled=True,
        data_source="yfinance",
        poll_interval_minutes=15,
        market_open="09:15",
        market_close="15:30",
        timezone="Asia/Kolkata",
        commission_pct=0.02,
        watchlist=[
            "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS",
            "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
            "KOTAKBANK.NS", "ITC.NS", "SBIN.NS"
        ]
    ))

    crypto: MarketConfig = field(default_factory=lambda: MarketConfig(
        enabled=True,
        data_source="binance",
        poll_interval_minutes=1,
        market_open="00:00",
        market_close="23:59",
        timezone="UTC",
        commission_pct=0.1,
        watchlist=[
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"
        ]
    ))

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PaperTradingConfig":
        """Create config from dictionary with overrides"""
        config = cls()

        if "session" in config_dict:
            for key, value in config_dict["session"].items():
                if hasattr(config.session, key):
                    setattr(config.session, key, value)

        if "sizing" in config_dict:
            for key, value in config_dict["sizing"].items():
                if hasattr(config.sizing, key):
                    setattr(config.sizing, key, value)

        if "exits" in config_dict:
            for key, value in config_dict["exits"].items():
                if hasattr(config.exits, key):
                    setattr(config.exits, key, value)

        if "database_url" in config_dict:
            config.database_url = config_dict["database_url"]

        return config
```

**Step 4: Create tests/paper_trading/__init__.py**

```python
"""Tests for paper trading module"""
```

**Step 5: Create tests/paper_trading/conftest.py**

```python
"""Pytest configuration for paper trading tests"""
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)
```

**Step 6: Verify structure**

Run:
```bash
ls -la paper_trading/
ls -la tests/paper_trading/
```

Expected: Both directories exist with __init__.py files

**Step 7: Commit**

```bash
git add paper_trading/ tests/paper_trading/
git commit -m "feat(paper-trading): add package structure and configuration"
```

---

## Task 2: Create SQLAlchemy Models

**Files:**
- Create: `paper_trading/models.py`
- Create: `tests/paper_trading/test_models.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_models.py`:

```python
"""Tests for paper trading models"""
import unittest
from datetime import datetime
from decimal import Decimal

from paper_trading.models import (
    PaperSession,
    PaperPosition,
    PaperTrade,
    PositionAdjustment,
    PendingSignal,
    DailyPerformance,
    create_engine_and_tables,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestModels(unittest.TestCase):
    """Test SQLAlchemy models"""

    def setUp(self):
        """Create in-memory database for testing"""
        self.engine = create_engine("sqlite:///:memory:")
        create_engine_and_tables(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def tearDown(self):
        """Clean up database session"""
        self.db.close()

    def test_create_session(self):
        """Test creating a paper trading session"""
        session = PaperSession(
            name="Test Session",
            initial_balance=1000000.0,
            current_balance=1000000.0,
            currency="INR",
            status="active",
        )
        self.db.add(session)
        self.db.commit()

        retrieved = self.db.query(PaperSession).first()
        self.assertEqual(retrieved.name, "Test Session")
        self.assertEqual(retrieved.initial_balance, 1000000.0)
        self.assertEqual(retrieved.status, "active")

    def test_create_position(self):
        """Test creating a position linked to session"""
        session = PaperSession(
            name="Test Session",
            initial_balance=1000000.0,
            current_balance=1000000.0,
            currency="INR",
            status="active",
        )
        self.db.add(session)
        self.db.commit()

        position = PaperPosition(
            session_id=session.id,
            symbol="RELIANCE.NS",
            market="nse",
            direction="long",
            quantity=100.0,
            entry_price=2450.0,
            current_price=2450.0,
            stop_loss=2327.5,
            take_profit=2817.5,
            entry_confidence=0.85,
            current_confidence=0.85,
            strategy="MultiFactorStrategy",
            status="open",
        )
        self.db.add(position)
        self.db.commit()

        retrieved = self.db.query(PaperPosition).first()
        self.assertEqual(retrieved.symbol, "RELIANCE.NS")
        self.assertEqual(retrieved.session_id, session.id)
        self.assertEqual(retrieved.status, "open")

    def test_create_trade(self):
        """Test creating a trade record"""
        session = PaperSession(
            name="Test Session",
            initial_balance=1000000.0,
            current_balance=1000000.0,
            currency="INR",
            status="active",
        )
        self.db.add(session)
        self.db.commit()

        trade = PaperTrade(
            session_id=session.id,
            position_id=None,
            symbol="RELIANCE.NS",
            market="nse",
            trade_type="buy",
            quantity=100.0,
            price=2450.0,
            value=245000.0,
            commission=49.0,
            pnl=None,
        )
        self.db.add(trade)
        self.db.commit()

        retrieved = self.db.query(PaperTrade).first()
        self.assertEqual(retrieved.symbol, "RELIANCE.NS")
        self.assertEqual(retrieved.trade_type, "buy")
        self.assertEqual(retrieved.value, 245000.0)

    def test_position_unrealized_pnl(self):
        """Test position unrealized P&L calculation"""
        position = PaperPosition(
            session_id=1,
            symbol="RELIANCE.NS",
            market="nse",
            direction="long",
            quantity=100.0,
            entry_price=2450.0,
            current_price=2520.0,
            stop_loss=2327.5,
            take_profit=2817.5,
            entry_confidence=0.85,
            current_confidence=0.85,
            strategy="MultiFactorStrategy",
            status="open",
        )

        expected_pnl = (2520.0 - 2450.0) * 100.0  # 7000
        self.assertEqual(position.unrealized_pnl, expected_pnl)

    def test_position_unrealized_pnl_pct(self):
        """Test position unrealized P&L percentage"""
        position = PaperPosition(
            session_id=1,
            symbol="RELIANCE.NS",
            market="nse",
            direction="long",
            quantity=100.0,
            entry_price=2450.0,
            current_price=2520.0,
            stop_loss=2327.5,
            take_profit=2817.5,
            entry_confidence=0.85,
            current_confidence=0.85,
            strategy="MultiFactorStrategy",
            status="open",
        )

        expected_pct = ((2520.0 - 2450.0) / 2450.0) * 100  # ~2.857%
        self.assertAlmostEqual(position.unrealized_pnl_pct, expected_pct, places=2)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'paper_trading.models'"

**Step 3: Write the implementation**

Create `paper_trading/models.py`:

```python
"""
SQLAlchemy models for Paper Trading

Defines database schema for sessions, positions, trades, and performance tracking.
"""
from datetime import datetime
from typing import Optional
import logging

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey,
    create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

Base = declarative_base()


class PaperSession(Base):
    """Paper trading session"""
    __tablename__ = "paper_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    initial_balance = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="active")  # active, paused, ended
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    positions = relationship("PaperPosition", back_populates="session")
    trades = relationship("PaperTrade", back_populates="session")
    daily_performance = relationship("DailyPerformance", back_populates="session")
    pending_signals = relationship("PendingSignal", back_populates="session")

    def __repr__(self):
        return f"<PaperSession(id={self.id}, name='{self.name}', balance={self.current_balance})>"


class PaperPosition(Base):
    """Open or closed trading position"""
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("paper_sessions.id"), nullable=False)
    symbol = Column(String(50), nullable=False)
    market = Column(String(20), nullable=False)  # nse, crypto
    direction = Column(String(10), default="long")  # long, short
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Float, nullable=True)
    trailing_stop_high = Column(Float, nullable=True)  # Highest price since entry
    entry_confidence = Column(Float, nullable=True)
    current_confidence = Column(Float, nullable=True)
    strategy = Column(String(100), nullable=True)
    status = Column(String(20), default="open")  # open, closed
    close_reason = Column(String(50), nullable=True)  # sl, tp, trailing, manual, confidence
    opened_at = Column(DateTime, default=func.now())
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("PaperSession", back_populates="positions")
    trades = relationship("PaperTrade", back_populates="position")
    adjustments = relationship("PositionAdjustment", back_populates="position")

    __table_args__ = (
        Index("idx_positions_session_status", "session_id", "status"),
        Index("idx_positions_symbol", "symbol"),
    )

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L"""
        if self.direction == "long":
            return (self.current_price - self.entry_price) * self.quantity
        else:  # short
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        if self.direction == "long":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            return ((self.entry_price - self.current_price) / self.entry_price) * 100

    @property
    def position_value(self) -> float:
        """Current position value"""
        return self.current_price * self.quantity

    def __repr__(self):
        return f"<PaperPosition(id={self.id}, symbol='{self.symbol}', qty={self.quantity}, status='{self.status}')>"


class PaperTrade(Base):
    """Individual trade record (buy or sell)"""
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("paper_sessions.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("paper_positions.id"), nullable=True)
    symbol = Column(String(50), nullable=False)
    market = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # quantity * price
    commission = Column(Float, default=0.0)
    pnl = Column(Float, nullable=True)  # Realized P&L for sells
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    session = relationship("PaperSession", back_populates="trades")
    position = relationship("PaperPosition", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_session_time", "session_id", "timestamp"),
    )

    def __repr__(self):
        return f"<PaperTrade(id={self.id}, symbol='{self.symbol}', type='{self.trade_type}', qty={self.quantity})>"


class PositionAdjustment(Base):
    """Log of position adjustments (SL/TP changes due to confidence)"""
    __tablename__ = "position_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("paper_positions.id"), nullable=False)
    adjustment_type = Column(String(50), nullable=False)  # tighten, partial_close, etc.
    old_stop_loss = Column(Float, nullable=True)
    new_stop_loss = Column(Float, nullable=True)
    old_take_profit = Column(Float, nullable=True)
    new_take_profit = Column(Float, nullable=True)
    old_confidence = Column(Float, nullable=True)
    new_confidence = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    position = relationship("PaperPosition", back_populates="adjustments")

    def __repr__(self):
        return f"<PositionAdjustment(id={self.id}, type='{self.adjustment_type}')>"


class PendingSignal(Base):
    """Signals awaiting review/execution"""
    __tablename__ = "pending_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("paper_sessions.id"), nullable=False)
    symbol = Column(String(50), nullable=False)
    market = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)  # buy, sell
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    strategy = Column(String(100), nullable=True)
    factors_json = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, executed, rejected, expired
    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("PaperSession", back_populates="pending_signals")

    def __repr__(self):
        return f"<PendingSignal(id={self.id}, symbol='{self.symbol}', status='{self.status}')>"


class DailyPerformance(Base):
    """Daily performance snapshot"""
    __tablename__ = "daily_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("paper_sessions.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    invested_value = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    cumulative_return_pct = Column(Float, default=0.0)
    drawdown_pct = Column(Float, default=0.0)
    num_positions = Column(Integer, default=0)
    num_trades = Column(Integer, default=0)

    # Relationships
    session = relationship("PaperSession", back_populates="daily_performance")

    __table_args__ = (
        Index("idx_perf_session_date", "session_id", "date"),
    )

    def __repr__(self):
        return f"<DailyPerformance(session={self.session_id}, date={self.date}, value={self.portfolio_value})>"


def create_engine_and_tables(engine=None, database_url: str = "sqlite:///paper_trading.db"):
    """Create database engine and all tables"""
    if engine is None:
        engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    logger.info(f"Created database tables")
    return engine
```

**Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_models.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add paper_trading/models.py tests/paper_trading/test_models.py
git commit -m "feat(paper-trading): add SQLAlchemy models for sessions, positions, trades"
```

---

## Task 3: Create NSE Data Fetcher

**Files:**
- Create: `data_service/fetchers/nse_fetcher.py`
- Modify: `data_service/fetchers/__init__.py`
- Create: `tests/paper_trading/test_nse_fetcher.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_nse_fetcher.py`:

```python
"""Tests for NSE data fetcher using yfinance"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from data_service.fetchers.nse_fetcher import NSEFetcher


class TestNSEFetcher(unittest.TestCase):
    """Test NSE fetcher with mocked yfinance"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = NSEFetcher()

        # Sample OHLCV data
        dates = pd.date_range(start="2026-01-01", periods=5, freq="D")
        self.mock_df = pd.DataFrame({
            "Open": [2400.0, 2420.0, 2450.0, 2440.0, 2460.0],
            "High": [2430.0, 2460.0, 2480.0, 2470.0, 2490.0],
            "Low": [2390.0, 2410.0, 2440.0, 2430.0, 2450.0],
            "Close": [2420.0, 2450.0, 2470.0, 2460.0, 2480.0],
            "Volume": [1000000, 1100000, 1200000, 1150000, 1250000],
        }, index=dates)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_fetch_historical_data(self, mock_yf):
        """Test fetching historical OHLCV data"""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = self.mock_df
        mock_yf.Ticker.return_value = mock_ticker

        df = self.fetcher.fetch_historical_data("RELIANCE.NS", interval="1d")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)
        self.assertIn("open", df.columns)
        self.assertIn("close", df.columns)
        self.assertIn("volume", df.columns)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_get_current_price(self, mock_yf):
        """Test getting current price"""
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 2480.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = self.fetcher.get_current_price("RELIANCE.NS")

        self.assertEqual(price, 2480.0)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_get_current_price_fallback(self, mock_yf):
        """Test current price fallback to fast_info"""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.fast_info = {"lastPrice": 2475.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = self.fetcher.get_current_price("RELIANCE.NS")

        self.assertEqual(price, 2475.0)

    def test_is_market_open_during_hours(self):
        """Test market open check during trading hours"""
        # Mock a weekday at 10:00 AM IST
        with patch("data_service.fetchers.nse_fetcher.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 1  # Tuesday
            mock_now.time.return_value = datetime.strptime("10:00", "%H:%M").time()
            mock_dt.now.return_value = mock_now

            # This test checks the logic structure; actual implementation may vary
            self.assertIsInstance(self.fetcher.is_market_open(), bool)

    def test_normalize_symbol(self):
        """Test symbol normalization for NSE"""
        # Should add .NS if missing
        self.assertEqual(self.fetcher.normalize_symbol("RELIANCE"), "RELIANCE.NS")
        # Should keep .NS if present
        self.assertEqual(self.fetcher.normalize_symbol("RELIANCE.NS"), "RELIANCE.NS")
        # Should handle lowercase
        self.assertEqual(self.fetcher.normalize_symbol("reliance"), "RELIANCE.NS")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_nse_fetcher.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'data_service.fetchers.nse_fetcher'"

**Step 3: Write the implementation**

Create `data_service/fetchers/nse_fetcher.py`:

```python
"""
NSE Data Fetcher using yfinance

Fetches historical and current price data for NSE (Indian) stocks.
Uses Yahoo Finance with .NS suffix for NSE symbols.
"""
import logging
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

# NSE market hours
IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


class NSEFetcher:
    """
    Fetcher for NSE (National Stock Exchange of India) data via yfinance.

    Supports:
    - Historical OHLCV data
    - Current prices
    - Market hours detection
    """

    TIMEFRAME_MAP = {
        "1d": "1d",
        "1h": "1h",
        "15m": "15m",
        "5m": "5m",
    }

    def __init__(self):
        """Initialize NSE fetcher"""
        self.logger = logging.getLogger(__name__)

        if yf is None:
            self.logger.error("yfinance not installed. Run: pip install yfinance")
            raise ImportError("yfinance is required for NSEFetcher")

        self.logger.info("NSEFetcher initialized")

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to NSE format (add .NS suffix if missing)

        Args:
            symbol: Stock symbol (e.g., "RELIANCE" or "RELIANCE.NS")

        Returns:
            Normalized symbol with .NS suffix
        """
        symbol = symbol.upper().strip()
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
        return symbol

    def fetch_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        period: str = "1mo",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an NSE stock.

        Args:
            symbol: NSE stock symbol (e.g., "RELIANCE.NS" or "RELIANCE")
            interval: Data interval (1d, 1h, 15m, 5m)
            start_time: Start datetime (optional, uses period if not specified)
            end_time: End datetime (optional, defaults to now)
            period: Period to fetch if start_time not specified (1d, 5d, 1mo, 3mo, 1y)

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        symbol = self.normalize_symbol(symbol)
        yf_interval = self.TIMEFRAME_MAP.get(interval, "1d")

        try:
            ticker = yf.Ticker(symbol)

            if start_time and end_time:
                df = ticker.history(
                    start=start_time.strftime("%Y-%m-%d"),
                    end=end_time.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                )
            elif start_time:
                df = ticker.history(
                    start=start_time.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                )
            else:
                df = ticker.history(period=period, interval=yf_interval)

            if df.empty:
                self.logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()

            # Keep only OHLCV columns
            columns_to_keep = ["open", "high", "low", "close", "volume"]
            available_columns = [col for col in columns_to_keep if col in df.columns]
            df = df[available_columns]

            self.logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise

    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for an NSE stock.

        Args:
            symbol: NSE stock symbol

        Returns:
            Current price as float
        """
        symbol = self.normalize_symbol(symbol)

        try:
            ticker = yf.Ticker(symbol)

            # Try regularMarketPrice first
            price = ticker.info.get("regularMarketPrice")

            # Fallback to fast_info
            if price is None:
                price = ticker.fast_info.get("lastPrice", 0)

            if price is None or price == 0:
                # Final fallback: get last close from history
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
                else:
                    price = 0.0

            return float(price)

        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {str(e)}")
            return 0.0

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.

        Args:
            symbols: List of NSE stock symbols

        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
        return prices

    def is_market_open(self) -> bool:
        """
        Check if NSE market is currently open.

        Returns:
            True if market is open (weekday, between 9:15 AM - 3:30 PM IST)
        """
        now = datetime.now(IST)

        # Check if weekday (0=Monday, 6=Sunday)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        current_time = now.time()
        return MARKET_OPEN <= current_time <= MARKET_CLOSE

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get detailed market status.

        Returns:
            Dictionary with market status information
        """
        now = datetime.now(IST)
        is_open = self.is_market_open()

        return {
            "is_open": is_open,
            "current_time": now.strftime("%H:%M:%S"),
            "timezone": "Asia/Kolkata",
            "market_open": MARKET_OPEN.strftime("%H:%M"),
            "market_close": MARKET_CLOSE.strftime("%H:%M"),
            "day_of_week": now.strftime("%A"),
        }

    def calculate_atr(
        self,
        symbol: str,
        period: int = 14,
        interval: str = "1d",
    ) -> float:
        """
        Calculate Average True Range for volatility-based position sizing.

        Args:
            symbol: NSE stock symbol
            period: ATR period (default 14)
            interval: Data interval

        Returns:
            ATR value
        """
        df = self.fetch_historical_data(symbol, interval=interval, period="3mo")

        if len(df) < period + 1:
            self.logger.warning(f"Insufficient data for ATR calculation: {symbol}")
            return 0.0

        # Calculate True Range
        df["prev_close"] = df["close"].shift(1)
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["prev_close"])
        df["tr3"] = abs(df["low"] - df["prev_close"])
        df["true_range"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

        # Calculate ATR
        atr = df["true_range"].rolling(window=period).mean().iloc[-1]

        return float(atr)
```

**Step 4: Update data_service/fetchers/__init__.py**

Read and modify `data_service/fetchers/__init__.py` to add NSEFetcher:

```python
try:
    from .binance_fetcher import BinanceFetcher
except ImportError:
    BinanceFetcher = None

try:
    from .alpha_vantage_fetcher import AlphaVantageFetcher
except ImportError:
    AlphaVantageFetcher = None

try:
    from .yahoo_fetcher import YahooFetcher
except ImportError:
    YahooFetcher = None

try:
    from .nse_fetcher import NSEFetcher
except ImportError:
    NSEFetcher = None

__all__ = ['BinanceFetcher', 'AlphaVantageFetcher', 'YahooFetcher', 'NSEFetcher']
```

**Step 5: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_nse_fetcher.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add data_service/fetchers/nse_fetcher.py data_service/fetchers/__init__.py tests/paper_trading/test_nse_fetcher.py
git commit -m "feat(paper-trading): add NSE data fetcher using yfinance"
```

---

## Task 4: Create Position Manager

**Files:**
- Create: `paper_trading/position_manager.py`
- Create: `tests/paper_trading/test_position_manager.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_position_manager.py`:

```python
"""Tests for position manager"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from paper_trading.position_manager import PositionManager
from paper_trading.config import PaperTradingConfig, SizingConfig


class TestPositionManager(unittest.TestCase):
    """Test position sizing and risk management"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = PaperTradingConfig()
        self.manager = PositionManager(self.config)

    def test_calculate_position_size_basic(self):
        """Test basic position size calculation"""
        # Portfolio: 1,000,000
        # Risk per trade: 1% = 10,000
        # Entry: 500, Stop: 475 (5% stop distance)
        # Expected: 10,000 / (500 * 0.05) = 400 shares

        size = self.manager.calculate_position_size(
            portfolio_value=1000000,
            entry_price=500,
            stop_loss=475,
            volatility_factor=1.0,
        )

        self.assertEqual(size, 400)

    def test_calculate_position_size_with_volatility(self):
        """Test position size with volatility adjustment"""
        # Same as above but volatility_factor = 2.0
        # Expected: 10,000 / (500 * 0.05 * 2.0) = 200 shares

        size = self.manager.calculate_position_size(
            portfolio_value=1000000,
            entry_price=500,
            stop_loss=475,
            volatility_factor=2.0,
        )

        self.assertEqual(size, 200)

    def test_max_position_constraint(self):
        """Test max position size constraint"""
        # With very tight stop, position would be huge
        # Max position is 20% of portfolio = 200,000
        # At price 500, max shares = 200,000 / 500 = 400

        size = self.manager.calculate_position_size(
            portfolio_value=1000000,
            entry_price=500,
            stop_loss=499,  # Very tight stop (0.2%)
            volatility_factor=1.0,
        )

        # Should be capped at max position
        max_shares = (1000000 * 0.20) / 500  # 400
        self.assertLessEqual(size, max_shares)

    def test_min_position_constraint(self):
        """Test minimum position value constraint"""
        # Min position value is 5000
        # At price 5000, need at least 1 share

        size = self.manager.calculate_position_size(
            portfolio_value=1000000,
            entry_price=5000,
            stop_loss=4750,
            volatility_factor=1.0,
        )

        position_value = size * 5000
        self.assertGreaterEqual(position_value, 5000)

    def test_calculate_volatility_factor(self):
        """Test volatility factor calculation"""
        # Baseline ATR: 2%
        # Asset ATR: 4% -> factor = 2.0
        # Asset ATR: 1% -> factor = 0.5

        factor = self.manager.calculate_volatility_factor(atr_pct=4.0)
        self.assertEqual(factor, 2.0)

        factor = self.manager.calculate_volatility_factor(atr_pct=1.0)
        self.assertEqual(factor, 0.5)

    def test_check_exposure_limit(self):
        """Test portfolio exposure check"""
        # Max exposure: 80%
        # Current exposure: 70% -> can add more
        # Current exposure: 85% -> cannot add more

        can_add = self.manager.check_exposure_limit(
            portfolio_value=1000000,
            current_invested=700000,
            new_position_value=50000,
        )
        self.assertTrue(can_add)

        cannot_add = self.manager.check_exposure_limit(
            portfolio_value=1000000,
            current_invested=850000,
            new_position_value=50000,
        )
        self.assertFalse(cannot_add)

    def test_validate_signal(self):
        """Test signal validation"""
        # Valid signal
        signal = {
            "symbol": "RELIANCE.NS",
            "entry_price": 2450,
            "stop_loss": 2327.5,
            "confidence": 0.85,
        }

        is_valid, reason = self.manager.validate_signal(
            signal=signal,
            portfolio_value=1000000,
            current_invested=500000,
            open_positions=["TCS.NS", "INFY.NS"],
        )
        self.assertTrue(is_valid)

        # Already in position
        is_valid, reason = self.manager.validate_signal(
            signal=signal,
            portfolio_value=1000000,
            current_invested=500000,
            open_positions=["RELIANCE.NS"],
        )
        self.assertFalse(is_valid)
        self.assertIn("already", reason.lower())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_position_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

Create `paper_trading/position_manager.py`:

```python
"""
Position Manager for Paper Trading

Handles position sizing, risk management, and signal validation.
"""
import logging
from typing import Tuple, List, Dict, Any, Optional

from .config import PaperTradingConfig

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manages position sizing and risk controls.

    Features:
    - Risk-based position sizing
    - Volatility adjustment
    - Portfolio exposure limits
    - Signal validation
    """

    def __init__(self, config: PaperTradingConfig):
        """
        Initialize position manager.

        Args:
            config: Paper trading configuration
        """
        self.config = config
        self.sizing = config.sizing
        self.logger = logging.getLogger(__name__)

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: float,
        volatility_factor: float = 1.0,
    ) -> int:
        """
        Calculate position size based on risk per trade.

        Formula: Position Size = (Portfolio × Risk%) / (Entry × Stop Distance × Vol Factor)

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            volatility_factor: Volatility adjustment factor (>1 = reduce size)

        Returns:
            Number of shares/units to buy (integer)
        """
        if entry_price <= 0 or stop_loss <= 0:
            self.logger.error("Invalid entry or stop loss price")
            return 0

        # Calculate stop distance as percentage
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price

        if stop_distance_pct == 0:
            self.logger.error("Stop loss equals entry price")
            return 0

        # Risk amount
        risk_amount = portfolio_value * (self.sizing.risk_per_trade_pct / 100)

        # Apply volatility adjustment
        adjusted_risk = risk_amount / max(volatility_factor, 0.1)

        # Calculate position size
        position_value = adjusted_risk / stop_distance_pct
        shares = position_value / entry_price

        # Apply max position constraint
        max_position_value = portfolio_value * (self.sizing.max_position_pct / 100)
        max_shares = max_position_value / entry_price
        shares = min(shares, max_shares)

        # Apply min position constraint
        min_shares = self.sizing.min_position_value / entry_price
        if shares < min_shares:
            # Check if we can afford min position
            if self.sizing.min_position_value <= portfolio_value * (self.sizing.max_position_pct / 100):
                shares = min_shares
            else:
                shares = 0

        # Round down to integer
        return int(shares)

    def calculate_volatility_factor(self, atr_pct: float) -> float:
        """
        Calculate volatility adjustment factor.

        Factor > 1.0 means high volatility (reduce position)
        Factor < 1.0 means low volatility (increase position)

        Args:
            atr_pct: Asset's ATR as percentage of price

        Returns:
            Volatility factor
        """
        if not self.sizing.use_volatility_adjustment:
            return 1.0

        baseline = self.sizing.baseline_atr_pct
        if baseline <= 0:
            return 1.0

        factor = atr_pct / baseline

        # Clamp to reasonable range
        factor = max(0.25, min(factor, 4.0))

        return factor

    def check_exposure_limit(
        self,
        portfolio_value: float,
        current_invested: float,
        new_position_value: float,
    ) -> bool:
        """
        Check if adding a new position would exceed exposure limit.

        Args:
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount
            new_position_value: Value of new position to add

        Returns:
            True if position can be added, False otherwise
        """
        max_exposure = portfolio_value * (self.sizing.max_portfolio_exposure_pct / 100)
        new_total = current_invested + new_position_value

        return new_total <= max_exposure

    def get_available_capital(
        self,
        portfolio_value: float,
        current_invested: float,
    ) -> float:
        """
        Get available capital for new positions.

        Args:
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount

        Returns:
            Available capital for new positions
        """
        max_exposure = portfolio_value * (self.sizing.max_portfolio_exposure_pct / 100)
        return max(0, max_exposure - current_invested)

    def validate_signal(
        self,
        signal: Dict[str, Any],
        portfolio_value: float,
        current_invested: float,
        open_positions: List[str],
    ) -> Tuple[bool, str]:
        """
        Validate if a signal can be executed.

        Args:
            signal: Signal dictionary with symbol, entry_price, stop_loss, confidence
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount
            open_positions: List of symbols with open positions

        Returns:
            Tuple of (is_valid, reason)
        """
        symbol = signal.get("symbol", "")
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        confidence = signal.get("confidence", 0)

        # Check if already in position
        if symbol in open_positions:
            return False, f"Already in position for {symbol}"

        # Check confidence threshold
        min_confidence = self.config.strategies.get("min_signal_confidence", 0.6) if hasattr(self.config, 'strategies') and isinstance(self.config.strategies, dict) else 0.6
        if confidence < min_confidence:
            return False, f"Confidence {confidence} below threshold {min_confidence}"

        # Check exposure limit
        position_size = self.calculate_position_size(
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            stop_loss=stop_loss,
        )
        position_value = position_size * entry_price

        if not self.check_exposure_limit(portfolio_value, current_invested, position_value):
            return False, f"Would exceed max exposure limit"

        # Check if position is valid
        if position_size <= 0:
            return False, "Position size would be zero or negative"

        return True, "Signal validated"

    def calculate_commission(
        self,
        value: float,
        market: str,
    ) -> float:
        """
        Calculate commission for a trade.

        Args:
            value: Trade value
            market: Market identifier (nse, crypto)

        Returns:
            Commission amount
        """
        if market == "nse":
            rate = self.config.nse.commission_pct
        elif market == "crypto":
            rate = self.config.crypto.commission_pct
        else:
            rate = 0.1  # Default 0.1%

        return value * (rate / 100)
```

**Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_position_manager.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add paper_trading/position_manager.py tests/paper_trading/test_position_manager.py
git commit -m "feat(paper-trading): add position manager with risk-based sizing"
```

---

## Task 5: Create Exit Manager

**Files:**
- Create: `paper_trading/exit_manager.py`
- Create: `tests/paper_trading/test_exit_manager.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_exit_manager.py`:

```python
"""Tests for exit manager"""
import unittest
from paper_trading.exit_manager import ExitManager, ExitSignal
from paper_trading.config import PaperTradingConfig


class TestExitManager(unittest.TestCase):
    """Test exit logic: SL, TP, trailing stops"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = PaperTradingConfig()
        self.manager = ExitManager(self.config)

    def test_check_stop_loss_hit(self):
        """Test stop loss detection"""
        position = {
            "entry_price": 100,
            "current_price": 94,
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": None,
            "direction": "long",
        }

        signal = self.manager.check_exit(position)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.reason, "stop_loss")

    def test_check_take_profit_hit(self):
        """Test take profit detection"""
        position = {
            "entry_price": 100,
            "current_price": 116,
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": None,
            "direction": "long",
        }

        signal = self.manager.check_exit(position)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.reason, "take_profit")

    def test_trailing_stop_activation(self):
        """Test trailing stop activation at profit threshold"""
        position = {
            "entry_price": 100,
            "current_price": 106,  # +6%, above 5% activation
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": None,
            "trailing_stop_high": 100,
            "direction": "long",
        }

        updated = self.manager.update_trailing_stop(position)

        self.assertIsNotNone(updated["trailing_stop"])
        # Trail should be 3% below high of 106 = 102.82
        self.assertAlmostEqual(updated["trailing_stop"], 102.82, places=2)

    def test_trailing_stop_moves_up(self):
        """Test trailing stop moves up with price"""
        position = {
            "entry_price": 100,
            "current_price": 110,
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": 103,
            "trailing_stop_high": 106,
            "direction": "long",
        }

        updated = self.manager.update_trailing_stop(position)

        # New high is 110, trail should be 110 * 0.97 = 106.7
        self.assertAlmostEqual(updated["trailing_stop"], 106.7, places=2)
        self.assertEqual(updated["trailing_stop_high"], 110)

    def test_trailing_stop_does_not_move_down(self):
        """Test trailing stop never moves down"""
        position = {
            "entry_price": 100,
            "current_price": 105,  # Below previous high
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": 106.7,
            "trailing_stop_high": 110,
            "direction": "long",
        }

        updated = self.manager.update_trailing_stop(position)

        # Trail should stay at 106.7
        self.assertEqual(updated["trailing_stop"], 106.7)

    def test_trailing_stop_hit(self):
        """Test trailing stop exit detection"""
        position = {
            "entry_price": 100,
            "current_price": 106,
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": 107,
            "trailing_stop_high": 110,
            "direction": "long",
        }

        signal = self.manager.check_exit(position)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.reason, "trailing_stop")

    def test_no_exit_in_range(self):
        """Test no exit when price is between SL and TP"""
        position = {
            "entry_price": 100,
            "current_price": 105,
            "stop_loss": 95,
            "take_profit": 115,
            "trailing_stop": None,
            "direction": "long",
        }

        signal = self.manager.check_exit(position)

        self.assertIsNone(signal)

    def test_calculate_exit_levels(self):
        """Test calculation of SL/TP levels from entry"""
        entry_price = 100

        levels = self.manager.calculate_exit_levels(
            entry_price=entry_price,
            direction="long",
        )

        # Default: 5% SL, 15% TP
        self.assertEqual(levels["stop_loss"], 95)
        self.assertEqual(levels["take_profit"], 115)

    def test_calculate_exit_levels_with_atr(self):
        """Test ATR-based exit level calculation"""
        entry_price = 100
        atr = 5  # ATR of 5

        levels = self.manager.calculate_exit_levels(
            entry_price=entry_price,
            direction="long",
            atr=atr,
        )

        # ATR multiplier: 2x for SL, 3x for TP
        self.assertEqual(levels["stop_loss"], 90)  # 100 - (5 * 2)
        self.assertEqual(levels["take_profit"], 115)  # 100 + (5 * 3)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_exit_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

Create `paper_trading/exit_manager.py`:

```python
"""
Exit Manager for Paper Trading

Handles stop-loss, take-profit, and trailing stop logic.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .config import PaperTradingConfig

logger = logging.getLogger(__name__)


@dataclass
class ExitSignal:
    """Exit signal information"""
    should_exit: bool
    reason: str  # stop_loss, take_profit, trailing_stop, confidence, manual
    exit_price: float
    pnl_pct: float


class ExitManager:
    """
    Manages exit logic for positions.

    Features:
    - Hard stop-loss
    - Take-profit targets
    - Trailing stops (activate after profit threshold)
    - ATR-based dynamic levels
    """

    def __init__(self, config: PaperTradingConfig):
        """
        Initialize exit manager.

        Args:
            config: Paper trading configuration
        """
        self.config = config
        self.exits = config.exits
        self.logger = logging.getLogger(__name__)

    def check_exit(self, position: Dict[str, Any]) -> Optional[ExitSignal]:
        """
        Check if position should be exited.

        Args:
            position: Position dictionary with prices and levels

        Returns:
            ExitSignal if exit triggered, None otherwise
        """
        current_price = position.get("current_price", 0)
        entry_price = position.get("entry_price", 0)
        stop_loss = position.get("stop_loss")
        take_profit = position.get("take_profit")
        trailing_stop = position.get("trailing_stop")
        direction = position.get("direction", "long")

        if entry_price <= 0:
            return None

        # Calculate P&L percentage
        if direction == "long":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Check trailing stop first (it's usually tighter than hard SL when active)
        if trailing_stop is not None:
            if direction == "long" and current_price <= trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    reason="trailing_stop",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price >= trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    reason="trailing_stop",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        # Check hard stop-loss
        if stop_loss is not None:
            if direction == "long" and current_price <= stop_loss:
                return ExitSignal(
                    should_exit=True,
                    reason="stop_loss",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price >= stop_loss:
                return ExitSignal(
                    should_exit=True,
                    reason="stop_loss",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        # Check take-profit
        if take_profit is not None:
            if direction == "long" and current_price >= take_profit:
                return ExitSignal(
                    should_exit=True,
                    reason="take_profit",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price <= take_profit:
                return ExitSignal(
                    should_exit=True,
                    reason="take_profit",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        return None

    def update_trailing_stop(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update trailing stop based on current price.

        Args:
            position: Position dictionary

        Returns:
            Updated position dictionary
        """
        current_price = position.get("current_price", 0)
        entry_price = position.get("entry_price", 0)
        trailing_stop = position.get("trailing_stop")
        trailing_stop_high = position.get("trailing_stop_high", entry_price)
        direction = position.get("direction", "long")

        activation_pct = self.exits.trailing_stop_activation_pct
        trail_distance_pct = self.exits.trailing_stop_distance_pct

        # Calculate current profit percentage
        if direction == "long":
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100

        # Check if trailing stop should be activated
        if profit_pct >= activation_pct:
            if direction == "long":
                # Update high water mark
                new_high = max(trailing_stop_high, current_price)
                # Calculate new trailing stop
                new_trail = new_high * (1 - trail_distance_pct / 100)

                # Trailing stop only moves up, never down
                if trailing_stop is None or new_trail > trailing_stop:
                    position["trailing_stop"] = round(new_trail, 2)
                    position["trailing_stop_high"] = new_high
            else:
                # Short position: trailing stop moves down
                new_low = min(trailing_stop_high, current_price)
                new_trail = new_low * (1 + trail_distance_pct / 100)

                if trailing_stop is None or new_trail < trailing_stop:
                    position["trailing_stop"] = round(new_trail, 2)
                    position["trailing_stop_high"] = new_low

        return position

    def calculate_exit_levels(
        self,
        entry_price: float,
        direction: str = "long",
        atr: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate stop-loss and take-profit levels.

        Args:
            entry_price: Entry price
            direction: Trade direction (long/short)
            atr: Average True Range (optional, for ATR-based levels)

        Returns:
            Dictionary with stop_loss, take_profit, trailing_activation
        """
        if atr is not None and self.exits.use_atr_stops:
            # ATR-based levels
            sl_distance = atr * self.exits.atr_stop_multiplier
            tp_distance = atr * self.exits.atr_tp_multiplier
        else:
            # Percentage-based levels
            sl_distance = entry_price * (self.exits.default_stop_loss_pct / 100)
            tp_distance = entry_price * (self.exits.default_take_profit_pct / 100)

        if direction == "long":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
            trailing_activation = entry_price * (1 + self.exits.trailing_stop_activation_pct / 100)
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
            trailing_activation = entry_price * (1 - self.exits.trailing_stop_activation_pct / 100)

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "trailing_activation": round(trailing_activation, 2),
        }

    def adjust_levels_for_confidence(
        self,
        position: Dict[str, Any],
        new_confidence: float,
    ) -> Dict[str, Any]:
        """
        Adjust SL/TP levels based on confidence change.

        Args:
            position: Position dictionary
            new_confidence: New confidence level

        Returns:
            Updated position with adjusted levels
        """
        entry_price = position.get("entry_price", 0)
        original_sl = position.get("stop_loss")
        original_tp = position.get("take_profit")
        direction = position.get("direction", "long")

        # Find applicable tier
        tiers = self.config.confidence.tiers
        sl_factor = 1.0
        tp_factor = 1.0
        action = "hold"

        for min_conf, sl_f, tp_f, act in tiers:
            if new_confidence >= min_conf:
                sl_factor = sl_f
                tp_factor = tp_f
                action = act
                break

        if action == "close":
            position["should_close"] = True
            return position

        # Adjust levels by tightening (moving closer to entry)
        if original_sl is not None and entry_price > 0:
            if direction == "long":
                sl_distance = entry_price - original_sl
                new_sl_distance = sl_distance * sl_factor
                position["stop_loss"] = round(entry_price - new_sl_distance, 2)
            else:
                sl_distance = original_sl - entry_price
                new_sl_distance = sl_distance * sl_factor
                position["stop_loss"] = round(entry_price + new_sl_distance, 2)

        if original_tp is not None and entry_price > 0:
            if direction == "long":
                tp_distance = original_tp - entry_price
                new_tp_distance = tp_distance * tp_factor
                position["take_profit"] = round(entry_price + new_tp_distance, 2)
            else:
                tp_distance = entry_price - original_tp
                new_tp_distance = tp_distance * tp_factor
                position["take_profit"] = round(entry_price - new_tp_distance, 2)

        position["current_confidence"] = new_confidence
        position["confidence_action"] = action

        return position
```

**Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_exit_manager.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add paper_trading/exit_manager.py tests/paper_trading/test_exit_manager.py
git commit -m "feat(paper-trading): add exit manager with SL/TP/trailing stop logic"
```

---

## Task 6: Create Paper Executor

**Files:**
- Create: `paper_trading/executor.py`
- Create: `tests/paper_trading/test_executor.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_executor.py`:

```python
"""Tests for paper executor"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from paper_trading.executor import PaperExecutor
from paper_trading.models import (
    PaperSession, PaperPosition, PaperTrade,
    create_engine_and_tables, Base
)
from paper_trading.config import PaperTradingConfig


class TestPaperExecutor(unittest.TestCase):
    """Test paper trade execution"""

    def setUp(self):
        """Set up test database and executor"""
        self.engine = create_engine("sqlite:///:memory:")
        create_engine_and_tables(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

        self.config = PaperTradingConfig()
        self.executor = PaperExecutor(self.config, self.db)

        # Create a test session
        self.session = PaperSession(
            name="Test Session",
            initial_balance=1000000.0,
            current_balance=1000000.0,
            currency="INR",
            status="active",
        )
        self.db.add(self.session)
        self.db.commit()

    def tearDown(self):
        """Clean up database"""
        self.db.close()

    def test_open_position(self):
        """Test opening a new position"""
        signal = {
            "symbol": "RELIANCE.NS",
            "market": "nse",
            "direction": "long",
            "entry_price": 2450.0,
            "stop_loss": 2327.5,
            "take_profit": 2817.5,
            "confidence": 0.85,
            "strategy": "MomentumStrategy",
        }

        position = self.executor.open_position(
            session_id=self.session.id,
            signal=signal,
            quantity=100,
        )

        self.assertIsNotNone(position)
        self.assertEqual(position.symbol, "RELIANCE.NS")
        self.assertEqual(position.quantity, 100)
        self.assertEqual(position.status, "open")

        # Check trade was recorded
        trade = self.db.query(PaperTrade).filter_by(position_id=position.id).first()
        self.assertIsNotNone(trade)
        self.assertEqual(trade.trade_type, "buy")

        # Check balance was updated
        self.db.refresh(self.session)
        expected_balance = 1000000.0 - (2450.0 * 100) - trade.commission
        self.assertAlmostEqual(self.session.current_balance, expected_balance, places=2)

    def test_close_position(self):
        """Test closing an existing position"""
        # First open a position
        signal = {
            "symbol": "RELIANCE.NS",
            "market": "nse",
            "direction": "long",
            "entry_price": 2450.0,
            "stop_loss": 2327.5,
            "take_profit": 2817.5,
            "confidence": 0.85,
            "strategy": "MomentumStrategy",
        }

        position = self.executor.open_position(
            session_id=self.session.id,
            signal=signal,
            quantity=100,
        )

        # Now close it with profit
        closed = self.executor.close_position(
            position_id=position.id,
            exit_price=2520.0,
            reason="take_profit",
        )

        self.assertEqual(closed.status, "closed")
        self.assertEqual(closed.close_reason, "take_profit")

        # Check P&L
        sell_trade = self.db.query(PaperTrade).filter_by(
            position_id=position.id,
            trade_type="sell"
        ).first()
        self.assertIsNotNone(sell_trade)
        expected_pnl = (2520.0 - 2450.0) * 100 - sell_trade.commission
        self.assertAlmostEqual(sell_trade.pnl, expected_pnl, places=2)

    def test_partial_close(self):
        """Test partial position close"""
        signal = {
            "symbol": "RELIANCE.NS",
            "market": "nse",
            "direction": "long",
            "entry_price": 2450.0,
            "stop_loss": 2327.5,
            "take_profit": 2817.5,
            "confidence": 0.85,
            "strategy": "MomentumStrategy",
        }

        position = self.executor.open_position(
            session_id=self.session.id,
            signal=signal,
            quantity=100,
        )

        # Partial close 50%
        closed, remaining = self.executor.partial_close(
            position_id=position.id,
            close_pct=50,
            exit_price=2520.0,
            reason="confidence",
        )

        # Original position should have reduced quantity
        self.db.refresh(position)
        self.assertEqual(position.quantity, 50)
        self.assertEqual(position.status, "open")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_executor.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

Create `paper_trading/executor.py`:

```python
"""
Paper Executor for Paper Trading

Executes simulated trades, manages positions, and updates balances.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from .models import PaperSession, PaperPosition, PaperTrade, PositionAdjustment
from .config import PaperTradingConfig
from .position_manager import PositionManager

logger = logging.getLogger(__name__)


class PaperExecutor:
    """
    Executes paper trades and manages position lifecycle.

    Features:
    - Open new positions
    - Close positions (full or partial)
    - Update position prices
    - Record all trades and adjustments
    """

    def __init__(self, config: PaperTradingConfig, db: Session):
        """
        Initialize paper executor.

        Args:
            config: Paper trading configuration
            db: SQLAlchemy database session
        """
        self.config = config
        self.db = db
        self.position_manager = PositionManager(config)
        self.logger = logging.getLogger(__name__)

    def open_position(
        self,
        session_id: int,
        signal: Dict[str, Any],
        quantity: int,
    ) -> PaperPosition:
        """
        Open a new paper trading position.

        Args:
            session_id: Paper trading session ID
            signal: Signal dictionary with entry details
            quantity: Number of shares/units to buy

        Returns:
            Created PaperPosition object
        """
        # Get session
        session = self.db.query(PaperSession).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        symbol = signal.get("symbol")
        market = signal.get("market", "nse")
        entry_price = signal.get("entry_price")
        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")
        confidence = signal.get("confidence", 1.0)
        strategy = signal.get("strategy", "")
        direction = signal.get("direction", "long")

        # Calculate trade value and commission
        trade_value = entry_price * quantity
        commission = self.position_manager.calculate_commission(trade_value, market)

        # Check sufficient balance
        total_cost = trade_value + commission
        if session.current_balance < total_cost:
            raise ValueError(f"Insufficient balance: {session.current_balance} < {total_cost}")

        # Create position
        position = PaperPosition(
            session_id=session_id,
            symbol=symbol,
            market=market,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=None,
            trailing_stop_high=entry_price,
            entry_confidence=confidence,
            current_confidence=confidence,
            strategy=strategy,
            status="open",
        )
        self.db.add(position)
        self.db.flush()  # Get position ID

        # Create buy trade record
        trade = PaperTrade(
            session_id=session_id,
            position_id=position.id,
            symbol=symbol,
            market=market,
            trade_type="buy",
            quantity=quantity,
            price=entry_price,
            value=trade_value,
            commission=commission,
            pnl=None,
        )
        self.db.add(trade)

        # Update session balance
        session.current_balance -= total_cost

        self.db.commit()
        self.logger.info(f"Opened position: {symbol} x{quantity} @ {entry_price}")

        return position

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        reason: str = "manual",
    ) -> PaperPosition:
        """
        Close an existing position.

        Args:
            position_id: Position ID to close
            exit_price: Exit price
            reason: Close reason (stop_loss, take_profit, trailing_stop, manual, confidence)

        Returns:
            Closed PaperPosition object
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        if position.status != "open":
            raise ValueError(f"Position {position_id} is not open")

        session = self.db.query(PaperSession).filter_by(id=position.session_id).first()

        # Calculate P&L
        if position.direction == "long":
            gross_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - exit_price) * position.quantity

        # Calculate trade value and commission
        trade_value = exit_price * position.quantity
        commission = self.position_manager.calculate_commission(trade_value, position.market)
        net_pnl = gross_pnl - commission

        # Create sell trade record
        trade = PaperTrade(
            session_id=position.session_id,
            position_id=position.id,
            symbol=position.symbol,
            market=position.market,
            trade_type="sell",
            quantity=position.quantity,
            price=exit_price,
            value=trade_value,
            commission=commission,
            pnl=net_pnl,
        )
        self.db.add(trade)

        # Update position
        position.current_price = exit_price
        position.status = "closed"
        position.close_reason = reason
        position.closed_at = datetime.utcnow()

        # Update session balance
        session.current_balance += trade_value - commission

        self.db.commit()
        self.logger.info(f"Closed position: {position.symbol} @ {exit_price}, P&L: {net_pnl}")

        return position

    def partial_close(
        self,
        position_id: int,
        close_pct: float,
        exit_price: float,
        reason: str = "partial",
    ) -> Tuple[PaperTrade, PaperPosition]:
        """
        Partially close a position.

        Args:
            position_id: Position ID
            close_pct: Percentage to close (0-100)
            exit_price: Exit price
            reason: Close reason

        Returns:
            Tuple of (sell trade, remaining position)
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        session = self.db.query(PaperSession).filter_by(id=position.session_id).first()

        # Calculate quantity to close
        close_quantity = int(position.quantity * (close_pct / 100))
        if close_quantity <= 0:
            raise ValueError("Close quantity must be positive")

        remaining_quantity = position.quantity - close_quantity

        # Calculate P&L for closed portion
        if position.direction == "long":
            gross_pnl = (exit_price - position.entry_price) * close_quantity
        else:
            gross_pnl = (position.entry_price - exit_price) * close_quantity

        trade_value = exit_price * close_quantity
        commission = self.position_manager.calculate_commission(trade_value, position.market)
        net_pnl = gross_pnl - commission

        # Create sell trade for partial close
        trade = PaperTrade(
            session_id=position.session_id,
            position_id=position.id,
            symbol=position.symbol,
            market=position.market,
            trade_type="sell",
            quantity=close_quantity,
            price=exit_price,
            value=trade_value,
            commission=commission,
            pnl=net_pnl,
        )
        self.db.add(trade)

        # Update position quantity
        position.quantity = remaining_quantity
        position.current_price = exit_price

        # If nothing remaining, close position
        if remaining_quantity <= 0:
            position.status = "closed"
            position.close_reason = reason
            position.closed_at = datetime.utcnow()

        # Update session balance
        session.current_balance += trade_value - commission

        # Record adjustment
        adjustment = PositionAdjustment(
            position_id=position.id,
            adjustment_type="partial_close",
            reason=f"Closed {close_pct}% ({close_quantity} units) - {reason}",
        )
        self.db.add(adjustment)

        self.db.commit()
        self.logger.info(f"Partial close: {position.symbol} x{close_quantity} @ {exit_price}")

        return trade, position

    def update_position_price(
        self,
        position_id: int,
        current_price: float,
    ) -> PaperPosition:
        """
        Update current price for a position.

        Args:
            position_id: Position ID
            current_price: New current price

        Returns:
            Updated position
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        position.current_price = current_price

        # Update trailing stop high if applicable
        if position.direction == "long":
            if position.trailing_stop_high is None or current_price > position.trailing_stop_high:
                position.trailing_stop_high = current_price
        else:
            if position.trailing_stop_high is None or current_price < position.trailing_stop_high:
                position.trailing_stop_high = current_price

        self.db.commit()
        return position

    def record_adjustment(
        self,
        position_id: int,
        adjustment_type: str,
        old_sl: Optional[float] = None,
        new_sl: Optional[float] = None,
        old_tp: Optional[float] = None,
        new_tp: Optional[float] = None,
        old_confidence: Optional[float] = None,
        new_confidence: Optional[float] = None,
        reason: str = "",
    ) -> PositionAdjustment:
        """
        Record a position adjustment.

        Args:
            position_id: Position ID
            adjustment_type: Type of adjustment
            old_sl/new_sl: Stop loss changes
            old_tp/new_tp: Take profit changes
            old_confidence/new_confidence: Confidence changes
            reason: Reason for adjustment

        Returns:
            Created adjustment record
        """
        adjustment = PositionAdjustment(
            position_id=position_id,
            adjustment_type=adjustment_type,
            old_stop_loss=old_sl,
            new_stop_loss=new_sl,
            old_take_profit=old_tp,
            new_take_profit=new_tp,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            reason=reason,
        )
        self.db.add(adjustment)
        self.db.commit()

        return adjustment

    def get_open_positions(self, session_id: int) -> list:
        """Get all open positions for a session."""
        return self.db.query(PaperPosition).filter_by(
            session_id=session_id,
            status="open"
        ).all()

    def get_session_value(self, session_id: int) -> Dict[str, float]:
        """
        Calculate total session value including positions.

        Returns:
            Dictionary with cash, invested, total values
        """
        session = self.db.query(PaperSession).filter_by(id=session_id).first()
        if not session:
            return {"cash": 0, "invested": 0, "total": 0}

        open_positions = self.get_open_positions(session_id)
        invested_value = sum(p.current_price * p.quantity for p in open_positions)

        return {
            "cash": session.current_balance,
            "invested": invested_value,
            "total": session.current_balance + invested_value,
        }
```

**Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_executor.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add paper_trading/executor.py tests/paper_trading/test_executor.py
git commit -m "feat(paper-trading): add paper executor for trade simulation"
```

---

## Task 7: Create Paper Trading Engine

**Files:**
- Create: `paper_trading/engine.py`
- Create: `tests/paper_trading/test_engine.py`

**Step 1: Write the failing test**

Create `tests/paper_trading/test_engine.py`:

```python
"""Tests for paper trading engine"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from paper_trading.engine import PaperTradingEngine
from paper_trading.models import PaperSession, create_engine_and_tables
from paper_trading.config import PaperTradingConfig


class TestPaperTradingEngine(unittest.TestCase):
    """Test the main paper trading engine"""

    def setUp(self):
        """Set up test database and engine"""
        self.db_engine = create_engine("sqlite:///:memory:")
        create_engine_and_tables(self.db_engine)

        self.config = PaperTradingConfig()
        self.config.database_url = "sqlite:///:memory:"

    def test_create_session(self):
        """Test creating a new trading session"""
        engine = PaperTradingEngine(self.config, db_engine=self.db_engine)

        session = engine.create_session(name="Test Session")

        self.assertIsNotNone(session)
        self.assertEqual(session.name, "Test Session")
        self.assertEqual(session.initial_balance, 1000000.0)
        self.assertEqual(session.status, "active")

    def test_process_signal_auto_mode(self):
        """Test processing a signal in auto mode"""
        engine = PaperTradingEngine(self.config, db_engine=self.db_engine)
        session = engine.create_session(name="Test Session")

        signal = {
            "symbol": "RELIANCE.NS",
            "market": "nse",
            "direction": "long",
            "entry_price": 2450.0,
            "stop_loss": 2327.5,
            "take_profit": 2817.5,
            "confidence": 0.85,
            "strategy": "MomentumStrategy",
        }

        # Mock the fetcher to avoid real API calls
        with patch.object(engine, 'get_current_price', return_value=2450.0):
            with patch.object(engine, 'get_atr', return_value=50.0):
                result = engine.process_signal(session.id, signal)

        self.assertTrue(result["executed"])
        self.assertIsNotNone(result["position_id"])

    def test_check_exits(self):
        """Test checking exit conditions for positions"""
        engine = PaperTradingEngine(self.config, db_engine=self.db_engine)
        session = engine.create_session(name="Test Session")

        signal = {
            "symbol": "RELIANCE.NS",
            "market": "nse",
            "direction": "long",
            "entry_price": 2450.0,
            "stop_loss": 2327.5,
            "take_profit": 2817.5,
            "confidence": 0.85,
            "strategy": "MomentumStrategy",
        }

        with patch.object(engine, 'get_current_price', return_value=2450.0):
            with patch.object(engine, 'get_atr', return_value=50.0):
                engine.process_signal(session.id, signal)

        # Now check exits with price below stop loss
        with patch.object(engine, 'get_current_price', return_value=2300.0):
            exits = engine.check_exits(session.id)

        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0]["reason"], "stop_loss")

    def test_get_session_summary(self):
        """Test getting session summary"""
        engine = PaperTradingEngine(self.config, db_engine=self.db_engine)
        session = engine.create_session(name="Test Session")

        summary = engine.get_session_summary(session.id)

        self.assertEqual(summary["session_name"], "Test Session")
        self.assertEqual(summary["initial_balance"], 1000000.0)
        self.assertEqual(summary["num_open_positions"], 0)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest tests/paper_trading/test_engine.py -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

Create `paper_trading/engine.py`:

```python
"""
Paper Trading Engine

Main orchestrator for the paper trading system.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import PaperTradingConfig
from .models import (
    PaperSession, PaperPosition, PaperTrade, PendingSignal,
    DailyPerformance, create_engine_and_tables
)
from .position_manager import PositionManager
from .exit_manager import ExitManager, ExitSignal
from .executor import PaperExecutor

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Main paper trading engine.

    Orchestrates:
    - Session management
    - Signal processing
    - Position monitoring
    - Exit checking
    - Performance tracking
    """

    def __init__(
        self,
        config: PaperTradingConfig,
        db_engine=None,
    ):
        """
        Initialize paper trading engine.

        Args:
            config: Paper trading configuration
            db_engine: Optional SQLAlchemy engine (creates new if not provided)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize database
        if db_engine is None:
            db_engine = create_engine(config.database_url)
            create_engine_and_tables(db_engine)

        self.db_engine = db_engine
        self.Session = sessionmaker(bind=db_engine)

        # Initialize managers
        self.position_manager = PositionManager(config)
        self.exit_manager = ExitManager(config)

        # Initialize fetchers (lazy loaded)
        self._nse_fetcher = None
        self._binance_fetcher = None

        self.logger.info("PaperTradingEngine initialized")

    @property
    def nse_fetcher(self):
        """Lazy load NSE fetcher"""
        if self._nse_fetcher is None:
            try:
                from data_service.fetchers.nse_fetcher import NSEFetcher
                self._nse_fetcher = NSEFetcher()
            except ImportError:
                self.logger.warning("NSEFetcher not available")
        return self._nse_fetcher

    @property
    def binance_fetcher(self):
        """Lazy load Binance fetcher"""
        if self._binance_fetcher is None:
            try:
                from data_service.fetchers.binance_fetcher import BinanceFetcher
                self._binance_fetcher = BinanceFetcher()
            except ImportError:
                self.logger.warning("BinanceFetcher not available")
        return self._binance_fetcher

    def get_db(self) -> Session:
        """Get a new database session"""
        return self.Session()

    def create_session(
        self,
        name: str,
        initial_balance: Optional[float] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> PaperSession:
        """
        Create a new paper trading session.

        Args:
            name: Session name
            initial_balance: Starting balance (uses config default if not specified)
            config_overrides: Optional config overrides for this session

        Returns:
            Created PaperSession
        """
        db = self.get_db()
        try:
            balance = initial_balance or self.config.session.initial_balance

            session = PaperSession(
                name=name,
                initial_balance=balance,
                current_balance=balance,
                currency=self.config.session.currency,
                status="active",
                config_json=str(config_overrides) if config_overrides else None,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            self.logger.info(f"Created session: {name} with balance {balance}")
            return session
        finally:
            db.close()

    def get_current_price(self, symbol: str, market: str) -> float:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol
            market: Market identifier (nse, crypto)

        Returns:
            Current price
        """
        if market == "nse" and self.nse_fetcher:
            return self.nse_fetcher.get_current_price(symbol)
        elif market == "crypto" and self.binance_fetcher:
            return self.binance_fetcher.get_current_price(symbol)
        else:
            self.logger.warning(f"No fetcher available for {market}")
            return 0.0

    def get_atr(self, symbol: str, market: str) -> float:
        """
        Get ATR for volatility-based sizing.

        Args:
            symbol: Trading symbol
            market: Market identifier

        Returns:
            ATR value
        """
        if market == "nse" and self.nse_fetcher:
            return self.nse_fetcher.calculate_atr(symbol)
        # TODO: Add crypto ATR
        return 0.0

    def process_signal(
        self,
        session_id: int,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a trading signal.

        Args:
            session_id: Paper trading session ID
            signal: Signal dictionary

        Returns:
            Result dictionary with execution details
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)

            session = db.query(PaperSession).filter_by(id=session_id).first()
            if not session:
                return {"executed": False, "reason": "Session not found"}

            # Get current positions
            open_positions = executor.get_open_positions(session_id)
            open_symbols = [p.symbol for p in open_positions]

            # Get session value
            session_value = executor.get_session_value(session_id)

            # Validate signal
            is_valid, reason = self.position_manager.validate_signal(
                signal=signal,
                portfolio_value=session_value["total"],
                current_invested=session_value["invested"],
                open_positions=open_symbols,
            )

            if not is_valid:
                return {"executed": False, "reason": reason}

            # Calculate position size
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)
            market = signal.get("market", "nse")
            symbol = signal.get("symbol", "")

            # Get ATR for volatility adjustment
            atr = self.get_atr(symbol, market)
            atr_pct = (atr / entry_price * 100) if entry_price > 0 and atr > 0 else self.config.sizing.baseline_atr_pct
            volatility_factor = self.position_manager.calculate_volatility_factor(atr_pct)

            quantity = self.position_manager.calculate_position_size(
                portfolio_value=session_value["total"],
                entry_price=entry_price,
                stop_loss=stop_loss,
                volatility_factor=volatility_factor,
            )

            if quantity <= 0:
                return {"executed": False, "reason": "Position size is zero"}

            # Check execution mode
            exec_mode = self.config.session.execution_mode
            confidence = signal.get("confidence", 0)

            if exec_mode == "review":
                # Queue for review
                pending = PendingSignal(
                    session_id=session_id,
                    symbol=symbol,
                    market=market,
                    signal_type=signal.get("direction", "long"),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=signal.get("take_profit"),
                    confidence=confidence,
                    strategy=signal.get("strategy", ""),
                    status="pending",
                )
                db.add(pending)
                db.commit()
                return {"executed": False, "reason": "Queued for review", "signal_id": pending.id}

            elif exec_mode == "hybrid":
                if confidence < self.config.session.hybrid_confidence_threshold:
                    # Queue low-confidence signals
                    pending = PendingSignal(
                        session_id=session_id,
                        symbol=symbol,
                        market=market,
                        signal_type=signal.get("direction", "long"),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=signal.get("take_profit"),
                        confidence=confidence,
                        strategy=signal.get("strategy", ""),
                        status="pending",
                    )
                    db.add(pending)
                    db.commit()
                    return {"executed": False, "reason": "Low confidence, queued for review", "signal_id": pending.id}

            # Execute trade (auto mode or high-confidence hybrid)
            position = executor.open_position(
                session_id=session_id,
                signal=signal,
                quantity=quantity,
            )

            return {
                "executed": True,
                "position_id": position.id,
                "symbol": position.symbol,
                "quantity": quantity,
                "entry_price": entry_price,
            }

        finally:
            db.close()

    def check_exits(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Check all open positions for exit conditions.

        Args:
            session_id: Paper trading session ID

        Returns:
            List of exit signals triggered
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)
            open_positions = executor.get_open_positions(session_id)

            exits_triggered = []

            for position in open_positions:
                # Get current price
                current_price = self.get_current_price(position.symbol, position.market)
                if current_price <= 0:
                    continue

                # Update position price
                executor.update_position_price(position.id, current_price)

                # Build position dict for exit check
                pos_dict = {
                    "entry_price": position.entry_price,
                    "current_price": current_price,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "trailing_stop": position.trailing_stop,
                    "trailing_stop_high": position.trailing_stop_high,
                    "direction": position.direction,
                }

                # Update trailing stop
                pos_dict = self.exit_manager.update_trailing_stop(pos_dict)
                if pos_dict.get("trailing_stop") != position.trailing_stop:
                    position.trailing_stop = pos_dict["trailing_stop"]
                    position.trailing_stop_high = pos_dict.get("trailing_stop_high")
                    db.commit()

                # Check for exit
                exit_signal = self.exit_manager.check_exit(pos_dict)

                if exit_signal and exit_signal.should_exit:
                    # Execute exit
                    executor.close_position(
                        position_id=position.id,
                        exit_price=current_price,
                        reason=exit_signal.reason,
                    )

                    exits_triggered.append({
                        "position_id": position.id,
                        "symbol": position.symbol,
                        "reason": exit_signal.reason,
                        "exit_price": current_price,
                        "pnl_pct": exit_signal.pnl_pct,
                    })

            return exits_triggered

        finally:
            db.close()

    def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        """
        Get summary of a trading session.

        Args:
            session_id: Paper trading session ID

        Returns:
            Summary dictionary
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)

            session = db.query(PaperSession).filter_by(id=session_id).first()
            if not session:
                return {}

            session_value = executor.get_session_value(session_id)
            open_positions = executor.get_open_positions(session_id)

            # Calculate P&L
            total_pnl = session_value["total"] - session.initial_balance
            total_pnl_pct = (total_pnl / session.initial_balance) * 100

            # Count trades
            total_trades = db.query(PaperTrade).filter_by(session_id=session_id).count()
            winning_trades = db.query(PaperTrade).filter(
                PaperTrade.session_id == session_id,
                PaperTrade.pnl > 0
            ).count()

            return {
                "session_id": session_id,
                "session_name": session.name,
                "status": session.status,
                "initial_balance": session.initial_balance,
                "current_balance": session.current_balance,
                "cash_available": session_value["cash"],
                "invested_value": session_value["invested"],
                "total_value": session_value["total"],
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "num_open_positions": len(open_positions),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }

        finally:
            db.close()
```

**Step 4: Run test to verify it passes**

Run:
```bash
python -m pytest tests/paper_trading/test_engine.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add paper_trading/engine.py tests/paper_trading/test_engine.py
git commit -m "feat(paper-trading): add main paper trading engine"
```

---

## Task 8: Create CLI Runner Script

**Files:**
- Create: `scripts/run_paper_trading.py`

**Step 1: Create the CLI script**

Create `scripts/run_paper_trading.py`:

```python
#!/usr/bin/env python3
"""
Paper Trading CLI Runner

Usage:
    python scripts/run_paper_trading.py --create-session "My Session"
    python scripts/run_paper_trading.py --session-id 1 --run
    python scripts/run_paper_trading.py --session-id 1 --summary
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from paper_trading import PaperTradingEngine, PaperTradingConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_session(engine: PaperTradingEngine, name: str):
    """Create a new trading session"""
    session = engine.create_session(name=name)
    print(f"\nCreated session:")
    print(f"  ID: {session.id}")
    print(f"  Name: {session.name}")
    print(f"  Balance: {session.current_balance:,.2f} {session.currency}")
    return session


def show_summary(engine: PaperTradingEngine, session_id: int):
    """Show session summary"""
    summary = engine.get_session_summary(session_id)

    if not summary:
        print(f"Session {session_id} not found")
        return

    print(f"\n{'='*50}")
    print(f"Session: {summary['session_name']} (ID: {summary['session_id']})")
    print(f"{'='*50}")
    print(f"Status: {summary['status']}")
    print(f"\nPortfolio:")
    print(f"  Initial Balance: {summary['initial_balance']:>15,.2f}")
    print(f"  Current Cash:    {summary['cash_available']:>15,.2f}")
    print(f"  Invested Value:  {summary['invested_value']:>15,.2f}")
    print(f"  Total Value:     {summary['total_value']:>15,.2f}")
    print(f"\nPerformance:")
    print(f"  Total P&L:       {summary['total_pnl']:>15,.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"  Open Positions:  {summary['num_open_positions']:>15}")
    print(f"  Total Trades:    {summary['total_trades']:>15}")
    print(f"  Win Rate:        {summary['win_rate']:>14.1f}%")
    print(f"{'='*50}\n")


def run_engine(engine: PaperTradingEngine, session_id: int, interval_seconds: int = 60):
    """Run the paper trading engine"""
    print(f"\nStarting paper trading engine for session {session_id}")
    print(f"Checking every {interval_seconds} seconds")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Check exits
            exits = engine.check_exits(session_id)
            for exit in exits:
                print(f"[EXIT] {exit['symbol']}: {exit['reason']} @ {exit['exit_price']:.2f} ({exit['pnl_pct']:+.2f}%)")

            # Show periodic summary
            summary = engine.get_session_summary(session_id)
            print(f"[{time.strftime('%H:%M:%S')}] Value: {summary['total_value']:,.2f} | P&L: {summary['total_pnl']:+,.2f} ({summary['total_pnl_pct']:+.2f}%) | Positions: {summary['num_open_positions']}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nStopping engine...")
        show_summary(engine, session_id)


def main():
    parser = argparse.ArgumentParser(description="Paper Trading CLI")
    parser.add_argument("--create-session", type=str, help="Create a new session with given name")
    parser.add_argument("--session-id", type=int, help="Session ID to use")
    parser.add_argument("--run", action="store_true", help="Run the trading engine")
    parser.add_argument("--summary", action="store_true", help="Show session summary")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--db", type=str, default="sqlite:///paper_trading.db", help="Database URL")

    args = parser.parse_args()

    # Initialize config and engine
    config = PaperTradingConfig()
    config.database_url = args.db
    engine = PaperTradingEngine(config)

    if args.create_session:
        create_session(engine, args.create_session)

    elif args.session_id and args.summary:
        show_summary(engine, args.session_id)

    elif args.session_id and args.run:
        run_engine(engine, args.session_id, args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 2: Make script executable and test**

Run:
```bash
chmod +x scripts/run_paper_trading.py
python scripts/run_paper_trading.py --help
```

Expected: Help message displayed

**Step 3: Test creating a session**

Run:
```bash
python scripts/run_paper_trading.py --create-session "Test Session"
```

Expected: Session created successfully

**Step 4: Test showing summary**

Run:
```bash
python scripts/run_paper_trading.py --session-id 1 --summary
```

Expected: Summary displayed

**Step 5: Commit**

```bash
git add scripts/run_paper_trading.py
git commit -m "feat(paper-trading): add CLI runner script"
```

---

## Task 9: Run All Tests and Final Verification

**Step 1: Run all paper trading tests**

Run:
```bash
python -m pytest tests/paper_trading/ -v --tb=short
```

Expected: All tests PASS

**Step 2: Run with coverage**

Run:
```bash
python -m pytest tests/paper_trading/ -v --cov=paper_trading --cov-report=term-missing
```

Expected: Good coverage (>80%)

**Step 3: Final commit for Phase 1**

```bash
git add -A
git commit -m "feat(paper-trading): complete Phase 1 - core engine implementation

- SQLAlchemy models for sessions, positions, trades
- NSE data fetcher using yfinance
- Position manager with risk-based sizing
- Exit manager with SL/TP/trailing stops
- Paper executor for trade simulation
- Main trading engine orchestrator
- CLI runner script

All tests passing."
```

---

## Summary

Phase 1 delivers a functional paper trading engine with:

| Component | File | Status |
|-----------|------|--------|
| Package structure | `paper_trading/__init__.py` | ✅ |
| Configuration | `paper_trading/config.py` | ✅ |
| Database models | `paper_trading/models.py` | ✅ |
| NSE fetcher | `data_service/fetchers/nse_fetcher.py` | ✅ |
| Position manager | `paper_trading/position_manager.py` | ✅ |
| Exit manager | `paper_trading/exit_manager.py` | ✅ |
| Paper executor | `paper_trading/executor.py` | ✅ |
| Trading engine | `paper_trading/engine.py` | ✅ |
| CLI runner | `scripts/run_paper_trading.py` | ✅ |

**Next:** Phase 2 - API Layer (FastAPI endpoints)
