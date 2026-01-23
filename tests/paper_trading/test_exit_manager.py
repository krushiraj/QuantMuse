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
