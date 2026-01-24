"""Tests for confidence monitor."""
import pytest
from unittest.mock import MagicMock, patch
from paper_trading.confidence_monitor import ConfidenceMonitor, ConfidenceAction
from paper_trading.config import PaperTradingConfig, ConfidenceConfig, ConfidenceTier


@pytest.fixture
def config():
    """Create test configuration."""
    return PaperTradingConfig(
        confidence=ConfidenceConfig(
            enable_dynamic_management=True,
            recalc_interval_minutes=15,
            partial_close_pct=50.0,
            tiers=[
                ConfidenceTier(min_confidence=0.80, sl_factor=1.0, tp_factor=1.0, action="hold"),
                ConfidenceTier(min_confidence=0.60, sl_factor=0.8, tp_factor=0.7, action="tighten"),
                ConfidenceTier(min_confidence=0.40, sl_factor=0.6, tp_factor=0.5, action="partial_close"),
                ConfidenceTier(min_confidence=0.0, sl_factor=0.0, tp_factor=0.0, action="close"),
            ]
        )
    )


@pytest.fixture
def monitor(config):
    """Create confidence monitor."""
    return ConfidenceMonitor(config)


@pytest.fixture
def mock_position():
    """Create mock position."""
    position = MagicMock()
    position.id = 1
    position.symbol = "RELIANCE.NS"
    position.direction = "long"
    position.entry_price = 2500.0
    position.current_price = 2600.0
    position.stop_loss = 2375.0  # 5% below entry
    position.take_profit = 2875.0  # 15% above entry
    position.entry_confidence = 0.85
    position.current_confidence = 0.85
    position.strategy = "MomentumStrategy"
    return position


@pytest.fixture
def mock_short_position():
    """Create mock short position."""
    position = MagicMock()
    position.id = 2
    position.symbol = "BTCUSDT"
    position.direction = "short"
    position.entry_price = 50000.0
    position.current_price = 48000.0
    position.stop_loss = 52500.0  # 5% above entry for short
    position.take_profit = 42500.0  # 15% below entry for short
    position.entry_confidence = 0.85
    position.current_confidence = 0.85
    position.strategy = "MomentumStrategy"
    return position


class TestGetTier:
    """Tests for get_tier method."""

    def test_get_tier_high_confidence(self, monitor):
        """Test getting tier for high confidence."""
        tier = monitor.get_tier(0.85)
        assert tier.action == "hold"
        assert tier.sl_factor == 1.0

    def test_get_tier_boundary_high(self, monitor):
        """Test getting tier at high confidence boundary."""
        tier = monitor.get_tier(0.80)
        assert tier.action == "hold"

    def test_get_tier_medium_confidence(self, monitor):
        """Test getting tier for medium confidence."""
        tier = monitor.get_tier(0.65)
        assert tier.action == "tighten"
        assert tier.sl_factor == 0.8

    def test_get_tier_boundary_medium(self, monitor):
        """Test getting tier at medium confidence boundary."""
        tier = monitor.get_tier(0.60)
        assert tier.action == "tighten"

    def test_get_tier_low_confidence(self, monitor):
        """Test getting tier for low confidence."""
        tier = monitor.get_tier(0.45)
        assert tier.action == "partial_close"
        assert tier.sl_factor == 0.6

    def test_get_tier_boundary_low(self, monitor):
        """Test getting tier at low confidence boundary."""
        tier = monitor.get_tier(0.40)
        assert tier.action == "partial_close"

    def test_get_tier_very_low_confidence(self, monitor):
        """Test getting tier for very low confidence."""
        tier = monitor.get_tier(0.25)
        assert tier.action == "close"

    def test_get_tier_zero_confidence(self, monitor):
        """Test getting tier for zero confidence."""
        tier = monitor.get_tier(0.0)
        assert tier.action == "close"

    def test_get_tier_max_confidence(self, monitor):
        """Test getting tier for maximum confidence."""
        tier = monitor.get_tier(1.0)
        assert tier.action == "hold"


class TestEvaluatePosition:
    """Tests for evaluate_position method."""

    def test_evaluate_position_hold(self, monitor, mock_position):
        """Test evaluation returns hold for high confidence."""
        action = monitor.evaluate_position(mock_position, 0.85)
        assert action.action == "hold"
        assert action.new_stop_loss is None
        assert action.new_take_profit is None
        assert action.close_pct == 0.0

    def test_evaluate_position_tighten(self, monitor, mock_position):
        """Test evaluation returns tighten for medium confidence."""
        action = monitor.evaluate_position(mock_position, 0.65)
        assert action.action == "tighten"
        assert action.new_stop_loss is not None
        assert action.new_take_profit is not None
        # Stop loss should be tighter (higher for long position)
        assert action.new_stop_loss > mock_position.stop_loss
        # Take profit should be closer to entry (lower for long position)
        assert action.new_take_profit < mock_position.take_profit

    def test_evaluate_position_tighten_short(self, monitor, mock_short_position):
        """Test evaluation returns tighten for short position."""
        action = monitor.evaluate_position(mock_short_position, 0.65)
        assert action.action == "tighten"
        # Stop loss should be tighter (lower for short position)
        assert action.new_stop_loss < mock_short_position.stop_loss
        # Take profit should be closer to entry (higher for short position)
        assert action.new_take_profit > mock_short_position.take_profit

    def test_evaluate_position_partial_close(self, monitor, mock_position):
        """Test evaluation returns partial_close for low confidence."""
        action = monitor.evaluate_position(mock_position, 0.45)
        assert action.action == "partial_close"
        assert action.close_pct == 50.0
        assert action.new_stop_loss is not None
        assert action.new_take_profit is not None

    def test_evaluate_position_close(self, monitor, mock_position):
        """Test evaluation returns close for very low confidence."""
        action = monitor.evaluate_position(mock_position, 0.25)
        assert action.action == "close"
        assert action.close_pct == 100.0

    def test_evaluate_position_reason_includes_confidence(self, monitor, mock_position):
        """Test that action reason includes confidence values."""
        action = monitor.evaluate_position(mock_position, 0.65)
        assert "0.85" in action.reason  # old confidence
        assert "0.65" in action.reason  # new confidence

    def test_evaluate_position_uses_entry_confidence_if_current_none(self, monitor, mock_position):
        """Test that entry confidence is used if current confidence is None."""
        mock_position.current_confidence = None
        action = monitor.evaluate_position(mock_position, 0.65)
        assert "0.85" in action.reason  # entry_confidence used

    def test_evaluate_position_defaults_to_1_if_no_confidence(self, monitor, mock_position):
        """Test that 1.0 is used if both confidences are None."""
        mock_position.current_confidence = None
        mock_position.entry_confidence = None
        action = monitor.evaluate_position(mock_position, 0.65)
        assert "1.00" in action.reason


class TestApplyAction:
    """Tests for apply_action method."""

    def test_apply_action_tighten(self, monitor, mock_position):
        """Test applying tighten action."""
        db = MagicMock()
        action = ConfidenceAction(
            action="tighten",
            new_stop_loss=2400.0,
            new_take_profit=2800.0,
            reason="Test tighten"
        )

        changes = monitor.apply_action(db, mock_position, action, 0.65)

        assert changes["action"] == "tighten"
        assert changes["new_stop_loss"] == 2400.0
        assert changes["new_take_profit"] == 2800.0
        assert changes["new_confidence"] == 0.65
        assert mock_position.stop_loss == 2400.0
        assert mock_position.take_profit == 2800.0
        assert mock_position.current_confidence == 0.65
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_apply_action_partial_close(self, monitor, mock_position):
        """Test applying partial close action."""
        db = MagicMock()
        action = ConfidenceAction(
            action="partial_close",
            new_stop_loss=2420.0,
            new_take_profit=2750.0,
            close_pct=50.0,
            reason="Test partial close"
        )

        changes = monitor.apply_action(db, mock_position, action, 0.45)

        assert changes["action"] == "partial_close"
        assert changes["close_pct"] == 50.0
        assert "new_stop_loss" in changes
        db.add.assert_called_once()

    def test_apply_action_close(self, monitor, mock_position):
        """Test applying close action."""
        db = MagicMock()
        action = ConfidenceAction(
            action="close",
            close_pct=100.0,
            reason="Test close"
        )

        changes = monitor.apply_action(db, mock_position, action, 0.25)

        assert changes["action"] == "close"
        assert changes["should_close"] is True
        assert mock_position.current_confidence == 0.25

    def test_apply_action_hold(self, monitor, mock_position):
        """Test applying hold action (no adjustment recorded)."""
        db = MagicMock()
        action = ConfidenceAction(
            action="hold",
            reason="Test hold"
        )

        changes = monitor.apply_action(db, mock_position, action, 0.90)

        assert changes["action"] == "hold"
        assert "new_stop_loss" not in changes
        db.add.assert_not_called()  # No adjustment recorded for hold


class TestCheckAllPositions:
    """Tests for check_all_positions method."""

    def test_check_all_positions_with_changes(self, monitor):
        """Test checking all positions with some requiring changes."""
        db = MagicMock()

        # Create mock positions
        position1 = MagicMock()
        position1.id = 1
        position1.symbol = "RELIANCE.NS"
        position1.direction = "long"
        position1.entry_price = 2500.0
        position1.stop_loss = 2375.0
        position1.take_profit = 2875.0
        position1.current_confidence = 0.85
        position1.entry_confidence = 0.85
        position1.strategy = "MomentumStrategy"

        position2 = MagicMock()
        position2.id = 2
        position2.symbol = "HDFCBANK.NS"
        position2.direction = "long"
        position2.entry_price = 1500.0
        position2.stop_loss = 1425.0
        position2.take_profit = 1725.0
        position2.current_confidence = 0.70
        position2.entry_confidence = 0.70
        position2.strategy = "ValueStrategy"

        db.query.return_value.filter.return_value.all.return_value = [position1, position2]

        def confidence_provider(symbol, strategy):
            if symbol == "RELIANCE.NS":
                return 0.85  # Hold
            return 0.65  # Tighten (0.60-0.79 range)

        changes = monitor.check_all_positions(db, 1, confidence_provider)

        # Only position2 should have changes (tighten)
        assert len(changes) == 1
        assert changes[0]["position_id"] == 2
        assert changes[0]["action"] == "tighten"

    def test_check_all_positions_handles_errors(self, monitor):
        """Test that errors are handled gracefully."""
        db = MagicMock()

        position = MagicMock()
        position.id = 1
        position.symbol = "ERROR.NS"
        position.strategy = "TestStrategy"

        db.query.return_value.filter.return_value.all.return_value = [position]

        def failing_provider(symbol, strategy):
            raise ValueError("Test error")

        changes = monitor.check_all_positions(db, 1, failing_provider)

        assert len(changes) == 1
        assert changes[0]["position_id"] == 1
        assert "error" in changes[0]
        assert "Test error" in changes[0]["error"]

    def test_check_all_positions_empty(self, monitor):
        """Test checking when no open positions."""
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        changes = monitor.check_all_positions(db, 1, lambda s, st: 0.5)

        assert len(changes) == 0

    def test_check_all_positions_updates_confidence_on_hold(self, monitor):
        """Test that confidence is updated even when action is hold."""
        db = MagicMock()

        position = MagicMock()
        position.id = 1
        position.symbol = "RELIANCE.NS"
        position.direction = "long"
        position.entry_price = 2500.0
        position.stop_loss = 2375.0
        position.take_profit = 2875.0
        position.current_confidence = 0.85
        position.entry_confidence = 0.85
        position.strategy = "MomentumStrategy"

        db.query.return_value.filter.return_value.all.return_value = [position]

        changes = monitor.check_all_positions(db, 1, lambda s, st: 0.90)

        # No changes returned for hold
        assert len(changes) == 0
        # But confidence should be updated
        assert position.current_confidence == 0.90


class TestConfidenceAction:
    """Tests for ConfidenceAction dataclass."""

    def test_confidence_action_defaults(self):
        """Test default values for ConfidenceAction."""
        action = ConfidenceAction(action="hold")
        assert action.new_stop_loss is None
        assert action.new_take_profit is None
        assert action.close_pct == 0.0
        assert action.reason == ""

    def test_confidence_action_with_values(self):
        """Test ConfidenceAction with all values."""
        action = ConfidenceAction(
            action="partial_close",
            new_stop_loss=100.0,
            new_take_profit=150.0,
            close_pct=50.0,
            reason="Low confidence"
        )
        assert action.action == "partial_close"
        assert action.new_stop_loss == 100.0
        assert action.new_take_profit == 150.0
        assert action.close_pct == 50.0
        assert action.reason == "Low confidence"


class TestConfidenceMonitorInit:
    """Tests for ConfidenceMonitor initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        monitor = ConfidenceMonitor()
        assert monitor.config is not None
        assert monitor.confidence_config is not None

    def test_init_with_custom_config(self, config):
        """Test initialization with custom config."""
        monitor = ConfidenceMonitor(config)
        assert monitor.config == config
        assert monitor.confidence_config.partial_close_pct == 50.0
