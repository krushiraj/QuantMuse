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
