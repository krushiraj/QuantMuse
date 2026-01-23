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
