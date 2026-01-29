# api/schemas.py
"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# === Session Schemas ===

class SessionCreate(BaseModel):
    """Schema for creating a new trading session."""
    name: str = Field(..., min_length=1, max_length=100)
    initial_balance: float = Field(..., gt=0)

    @field_validator('initial_balance')
    @classmethod
    def validate_balance(cls, v):
        if v <= 0:
            raise ValueError('Initial balance must be positive')
        return v


class SessionResponse(BaseModel):
    """Schema for session response."""
    id: int
    name: str
    initial_balance: float
    current_balance: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    """Schema for session summary with portfolio stats."""
    id: int
    name: str
    initial_balance: float
    current_balance: float
    portfolio_value: float
    cash_balance: float
    invested_value: float
    total_pnl: float
    total_pnl_pct: float
    open_positions: int
    total_trades: int
    status: str


# === Position Schemas ===

class PositionResponse(BaseModel):
    """Schema for position response."""
    id: int
    session_id: int
    symbol: str
    market: str
    direction: str
    quantity: float  # Float to support fractional crypto quantities
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float]
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    unrealized_pnl: float
    unrealized_pnl_pct: float

    model_config = {"from_attributes": True}


class PositionClose(BaseModel):
    """Schema for closing a position."""
    reason: str = Field(default="manual", max_length=50)
    close_price: Optional[float] = None


# === Trade Schemas ===

class TradeResponse(BaseModel):
    """Schema for trade response."""
    id: int
    session_id: int
    position_id: Optional[int]
    symbol: str
    trade_type: str
    quantity: float  # Float to support fractional crypto quantities
    price: float
    value: float
    commission: float
    pnl: Optional[float] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class TradeStats(BaseModel):
    """Schema for trade statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float


# === Signal Schemas ===

class SignalCreate(BaseModel):
    """Schema for creating a signal (for testing/manual entry)."""
    symbol: str
    market: str = Field(..., pattern="^(nse|crypto)$")
    signal_type: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    strategy: str


class SignalResponse(BaseModel):
    """Schema for signal response."""
    id: int
    session_id: int
    symbol: str
    market: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    factors_json: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SignalAction(BaseModel):
    """Schema for approving/rejecting a signal."""
    action: str = Field(..., pattern="^(approve|reject)$")


# === Performance Schemas ===

class DailyPerformanceResponse(BaseModel):
    """Schema for daily performance snapshot."""
    id: int
    session_id: int
    date: datetime
    portfolio_value: float
    cash_balance: float
    invested_value: float
    daily_pnl: float
    daily_return_pct: float
    cumulative_return_pct: float
    drawdown_pct: float
    num_positions: int
    num_trades: int

    model_config = {"from_attributes": True}


class PerformanceMetrics(BaseModel):
    """Schema for overall performance metrics."""
    total_return_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None


# === Market Schemas ===

class MarketPrice(BaseModel):
    """Schema for market price data."""
    symbol: str
    price: float
    change_pct: float
    volume: Optional[float] = None
    timestamp: datetime


class MarketStatus(BaseModel):
    """Schema for market status."""
    market: str
    is_open: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None


# === WebSocket Schemas ===

class WSMessage(BaseModel):
    """Schema for WebSocket messages."""
    type: str  # price_update, position_update, trade_executed, signal_generated
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
