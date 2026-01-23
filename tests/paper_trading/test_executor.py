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
        trade, remaining = self.executor.partial_close(
            position_id=position.id,
            close_pct=50,
            exit_price=2520.0,
            reason="confidence",
        )

        # Original position should have reduced quantity
        self.db.refresh(position)
        self.assertEqual(position.quantity, 50)
        self.assertEqual(position.status, "open")

    def test_get_session_value(self):
        """Test session value calculation"""
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

        self.executor.open_position(
            session_id=self.session.id,
            signal=signal,
            quantity=100,
        )

        value = self.executor.get_session_value(self.session.id)

        self.assertIn("cash", value)
        self.assertIn("invested", value)
        self.assertIn("total", value)
        self.assertGreater(value["invested"], 0)


if __name__ == "__main__":
    unittest.main()
