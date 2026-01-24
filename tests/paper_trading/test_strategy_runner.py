"""Tests for strategy runner and signal generator."""
import pytest
from datetime import datetime
from paper_trading.signal_generator import SignalGenerator, TradingSignal, SignalType
from paper_trading.strategy_runner import StrategyRunner


class TestSignalGenerator:
    """Tests for SignalGenerator."""

    @pytest.fixture
    def generator(self):
        return SignalGenerator(
            default_stop_loss_pct=5.0,
            default_take_profit_pct=15.0,
            min_confidence=0.6,
        )

    def test_generate_buy_signal(self, generator):
        """Test generating a BUY signal."""
        output = {"signal": 1, "confidence": 0.8, "factors": {"momentum": 0.7}}

        signal = generator.generate_signal(
            symbol="RELIANCE.NS",
            market="nse",
            strategy_name="MomentumStrategy",
            strategy_output=output,
            current_price=2500.0,
        )

        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.8
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price

    def test_generate_sell_signal(self, generator):
        """Test generating a SELL signal."""
        output = {"signal": -1, "confidence": 0.75, "factors": {"momentum": -0.5}}

        signal = generator.generate_signal(
            symbol="BTCUSDT",
            market="crypto",
            strategy_name="MomentumStrategy",
            strategy_output=output,
            current_price=50000.0,
        )

        assert signal is not None
        assert signal.signal_type == SignalType.SELL
        assert signal.stop_loss > signal.entry_price
        assert signal.take_profit < signal.entry_price

    def test_skip_low_confidence(self, generator):
        """Test that low confidence signals are skipped."""
        output = {"signal": 1, "confidence": 0.4}

        signal = generator.generate_signal(
            symbol="TCS.NS",
            market="nse",
            strategy_name="Test",
            strategy_output=output,
            current_price=3500.0,
        )

        assert signal is None

    def test_skip_hold_signal(self, generator):
        """Test that HOLD signals are skipped."""
        output = {"signal": 0, "confidence": 0.9}

        signal = generator.generate_signal(
            symbol="TCS.NS",
            market="nse",
            strategy_name="Test",
            strategy_output=output,
            current_price=3500.0,
        )

        assert signal is None

    def test_atr_based_stops(self, generator):
        """Test ATR-based stop loss calculation."""
        output = {"signal": 1, "confidence": 0.8}

        signal = generator.generate_signal(
            symbol="RELIANCE.NS",
            market="nse",
            strategy_name="Test",
            strategy_output=output,
            current_price=2500.0,
            atr=50.0,  # 2% ATR
        )

        assert signal is not None
        # Stop should be 2 ATR away
        assert abs(signal.entry_price - signal.stop_loss) == pytest.approx(100.0)

    def test_filter_signals(self, generator):
        """Test signal filtering."""
        signals = [
            TradingSignal("A", "nse", SignalType.BUY, 100, 95, 115, 0.9, "S1"),
            TradingSignal("B", "nse", SignalType.BUY, 200, 190, 230, 0.7, "S2"),
            TradingSignal("C", "nse", SignalType.BUY, 300, 285, 345, 0.5, "S3"),
        ]

        filtered = generator.filter_signals(signals, max_signals=2)

        assert len(filtered) == 2
        assert filtered[0].confidence == 0.9  # Highest first
        assert filtered[1].confidence == 0.7


class TestStrategyRunner:
    """Tests for StrategyRunner."""

    @pytest.fixture
    def runner(self):
        return StrategyRunner()

    def test_register_strategy(self, runner):
        """Test strategy registration."""
        def mock_strategy(symbol, data):
            return {"signal": 1, "confidence": 0.8}

        runner.register_strategy("mock", mock_strategy)
        assert "mock" in runner._strategies

    def test_run_strategy(self, runner):
        """Test running a registered strategy."""
        def mock_strategy(symbol, data):
            return {"signal": 1, "confidence": 0.8}

        runner.register_strategy("mock", mock_strategy)
        result = runner.run_strategy("mock", "TEST", "nse", {})

        assert result is not None
        assert result["signal"] == 1

    def test_run_unregistered_strategy(self, runner):
        """Test running unregistered strategy returns None."""
        result = runner.run_strategy("nonexistent", "TEST", "nse", {})
        assert result is None

    def test_run_all_strategies(self, runner):
        """Test running all strategies."""
        def strategy1(symbol, data):
            return {"signal": 1, "confidence": 0.8}

        def strategy2(symbol, data):
            return {"signal": 1, "confidence": 0.7}

        runner.register_strategy("s1", strategy1)
        runner.register_strategy("s2", strategy2)

        signals = runner.run_all_strategies(
            symbol="TEST.NS",
            market="nse",
            data={},
            current_price=100.0,
        )

        assert len(signals) == 2
