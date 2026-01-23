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
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

Base = declarative_base()

# Default database engine and session factory
DATABASE_URL = "sqlite:///paper_trading.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
