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
