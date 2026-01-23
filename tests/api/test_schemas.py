# tests/api/test_schemas.py
import pytest
from datetime import datetime
from pydantic import ValidationError


def test_session_create_schema():
    """Test SessionCreate schema validation."""
    from api.schemas import SessionCreate

    # Valid input
    data = SessionCreate(name="Test Session", initial_balance=100000)
    assert data.name == "Test Session"
    assert data.initial_balance == 100000

    # Invalid - negative balance
    with pytest.raises(ValidationError):
        SessionCreate(name="Test", initial_balance=-1000)


def test_session_create_zero_balance():
    """Test SessionCreate rejects zero balance."""
    from api.schemas import SessionCreate

    with pytest.raises(ValidationError):
        SessionCreate(name="Test", initial_balance=0)


def test_session_create_empty_name():
    """Test SessionCreate rejects empty name."""
    from api.schemas import SessionCreate

    with pytest.raises(ValidationError):
        SessionCreate(name="", initial_balance=100000)


def test_session_create_name_too_long():
    """Test SessionCreate rejects name over 100 characters."""
    from api.schemas import SessionCreate

    with pytest.raises(ValidationError):
        SessionCreate(name="x" * 101, initial_balance=100000)


def test_session_response_schema():
    """Test SessionResponse schema."""
    from api.schemas import SessionResponse

    data = SessionResponse(
        id=1,
        name="Test Session",
        initial_balance=100000,
        current_balance=105000,
        status="active",
        created_at=datetime.now(),
    )
    assert data.id == 1
    assert data.status == "active"


def test_session_summary_schema():
    """Test SessionSummary schema."""
    from api.schemas import SessionSummary

    data = SessionSummary(
        id=1,
        name="Test Session",
        initial_balance=100000,
        current_balance=105000,
        portfolio_value=105000,
        cash_balance=50000,
        invested_value=55000,
        total_pnl=5000,
        total_pnl_pct=5.0,
        open_positions=2,
        total_trades=10,
        status="active",
    )
    assert data.portfolio_value == 105000
    assert data.total_pnl_pct == 5.0


def test_position_response_schema():
    """Test PositionResponse schema with computed fields."""
    from api.schemas import PositionResponse

    data = PositionResponse(
        id=1,
        session_id=1,
        symbol="RELIANCE.NS",
        market="nse",
        direction="long",
        quantity=100,
        entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2375.0,
        take_profit=2875.0,
        trailing_stop=None,
        status="open",
        opened_at=datetime.now(),
        unrealized_pnl=10000.0,
        unrealized_pnl_pct=4.0,
    )
    assert data.symbol == "RELIANCE.NS"
    assert data.unrealized_pnl == 10000.0


def test_position_response_with_closed_fields():
    """Test PositionResponse with closed position fields."""
    from api.schemas import PositionResponse

    data = PositionResponse(
        id=1,
        session_id=1,
        symbol="RELIANCE.NS",
        market="nse",
        direction="long",
        quantity=100,
        entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2375.0,
        take_profit=2875.0,
        trailing_stop=50.0,
        status="closed",
        opened_at=datetime.now(),
        closed_at=datetime.now(),
        close_reason="take_profit",
        unrealized_pnl=10000.0,
        unrealized_pnl_pct=4.0,
    )
    assert data.status == "closed"
    assert data.close_reason == "take_profit"
    assert data.trailing_stop == 50.0


def test_position_close_schema():
    """Test PositionClose schema."""
    from api.schemas import PositionClose

    # Default reason
    data = PositionClose()
    assert data.reason == "manual"

    # Custom reason and price
    data = PositionClose(reason="stop_loss", close_price=2400.0)
    assert data.reason == "stop_loss"
    assert data.close_price == 2400.0


def test_trade_response_schema():
    """Test TradeResponse schema."""
    from api.schemas import TradeResponse

    data = TradeResponse(
        id=1,
        session_id=1,
        position_id=1,
        symbol="RELIANCE.NS",
        trade_type="buy",
        quantity=100,
        price=2500.0,
        value=250000.0,
        commission=50.0,
        timestamp=datetime.now(),
    )
    assert data.trade_type == "buy"
    assert data.value == 250000.0


def test_trade_response_with_pnl():
    """Test TradeResponse with P&L for sell trades."""
    from api.schemas import TradeResponse

    data = TradeResponse(
        id=2,
        session_id=1,
        position_id=1,
        symbol="RELIANCE.NS",
        trade_type="sell",
        quantity=100,
        price=2600.0,
        value=260000.0,
        commission=52.0,
        pnl=9898.0,
        timestamp=datetime.now(),
    )
    assert data.pnl == 9898.0


def test_trade_stats_schema():
    """Test TradeStats schema."""
    from api.schemas import TradeStats

    data = TradeStats(
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        win_rate=65.0,
        total_pnl=50000.0,
        avg_win=5000.0,
        avg_loss=-2000.0,
        largest_win=15000.0,
        largest_loss=-8000.0,
    )
    assert data.win_rate == 65.0
    assert data.avg_loss == -2000.0


def test_signal_create_schema():
    """Test SignalCreate schema validation."""
    from api.schemas import SignalCreate

    data = SignalCreate(
        symbol="TCS.NS",
        market="nse",
        signal_type="BUY",
        entry_price=3500.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        confidence=0.85,
        strategy="MomentumStrategy",
    )
    assert data.market == "nse"
    assert data.signal_type == "BUY"


def test_signal_create_invalid_market():
    """Test SignalCreate rejects invalid market."""
    from api.schemas import SignalCreate

    with pytest.raises(ValidationError):
        SignalCreate(
            symbol="TCS.NS",
            market="invalid",
            signal_type="BUY",
            entry_price=3500.0,
            stop_loss=3325.0,
            take_profit=4025.0,
            confidence=0.85,
            strategy="MomentumStrategy",
        )


def test_signal_create_invalid_signal_type():
    """Test SignalCreate rejects invalid signal type."""
    from api.schemas import SignalCreate

    with pytest.raises(ValidationError):
        SignalCreate(
            symbol="TCS.NS",
            market="nse",
            signal_type="HOLD",
            entry_price=3500.0,
            stop_loss=3325.0,
            take_profit=4025.0,
            confidence=0.85,
            strategy="MomentumStrategy",
        )


def test_signal_create_invalid_confidence():
    """Test SignalCreate rejects confidence outside 0-1 range."""
    from api.schemas import SignalCreate

    with pytest.raises(ValidationError):
        SignalCreate(
            symbol="TCS.NS",
            market="nse",
            signal_type="BUY",
            entry_price=3500.0,
            stop_loss=3325.0,
            take_profit=4025.0,
            confidence=1.5,
            strategy="MomentumStrategy",
        )


def test_signal_create_negative_price():
    """Test SignalCreate rejects negative prices."""
    from api.schemas import SignalCreate

    with pytest.raises(ValidationError):
        SignalCreate(
            symbol="TCS.NS",
            market="nse",
            signal_type="BUY",
            entry_price=-100.0,
            stop_loss=3325.0,
            take_profit=4025.0,
            confidence=0.85,
            strategy="MomentumStrategy",
        )


def test_signal_response_schema():
    """Test SignalResponse schema."""
    from api.schemas import SignalResponse

    data = SignalResponse(
        id=1,
        session_id=1,
        symbol="TCS.NS",
        market="nse",
        signal_type="BUY",
        entry_price=3500.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        confidence=0.85,
        strategy="MomentumStrategy",
        status="pending",
        created_at=datetime.now(),
    )
    assert data.signal_type == "BUY"
    assert data.confidence == 0.85


def test_signal_response_with_factors():
    """Test SignalResponse with factors JSON."""
    from api.schemas import SignalResponse

    factors = {"rsi": 35, "macd_signal": "bullish", "volume_spike": True}
    data = SignalResponse(
        id=1,
        session_id=1,
        symbol="TCS.NS",
        market="nse",
        signal_type="BUY",
        entry_price=3500.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        confidence=0.85,
        strategy="MomentumStrategy",
        factors_json=factors,
        status="approved",
        created_at=datetime.now(),
        reviewed_at=datetime.now(),
    )
    assert data.factors_json == factors
    assert data.status == "approved"


def test_signal_action_schema():
    """Test SignalAction schema."""
    from api.schemas import SignalAction

    # Valid actions
    approve = SignalAction(action="approve")
    assert approve.action == "approve"

    reject = SignalAction(action="reject")
    assert reject.action == "reject"


def test_signal_action_invalid():
    """Test SignalAction rejects invalid action."""
    from api.schemas import SignalAction

    with pytest.raises(ValidationError):
        SignalAction(action="maybe")


def test_daily_performance_response_schema():
    """Test DailyPerformanceResponse schema."""
    from api.schemas import DailyPerformanceResponse

    data = DailyPerformanceResponse(
        id=1,
        session_id=1,
        date=datetime.now(),
        portfolio_value=105000.0,
        cash_balance=50000.0,
        invested_value=55000.0,
        daily_pnl=1500.0,
        daily_return_pct=1.45,
        cumulative_return_pct=5.0,
        drawdown_pct=2.5,
        num_positions=3,
        num_trades=5,
    )
    assert data.daily_return_pct == 1.45
    assert data.drawdown_pct == 2.5


def test_performance_metrics_schema():
    """Test PerformanceMetrics schema."""
    from api.schemas import PerformanceMetrics

    data = PerformanceMetrics(
        total_return_pct=12.5,
        win_rate=65.0,
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        avg_win_pct=8.5,
        avg_loss_pct=-3.2,
        profit_factor=2.1,
        max_drawdown_pct=5.5,
        sharpe_ratio=1.8,
    )
    assert data.win_rate == 65.0
    assert data.profit_factor == 2.1


def test_performance_metrics_optional_ratios():
    """Test PerformanceMetrics with optional ratio fields."""
    from api.schemas import PerformanceMetrics

    data = PerformanceMetrics(
        total_return_pct=12.5,
        win_rate=65.0,
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        avg_win_pct=8.5,
        avg_loss_pct=-3.2,
        profit_factor=2.1,
        max_drawdown_pct=5.5,
        sharpe_ratio=1.8,
        sortino_ratio=2.5,
        calmar_ratio=3.0,
    )
    assert data.sortino_ratio == 2.5
    assert data.calmar_ratio == 3.0


def test_market_price_schema():
    """Test MarketPrice schema."""
    from api.schemas import MarketPrice

    data = MarketPrice(
        symbol="RELIANCE.NS",
        price=2550.0,
        change_pct=1.25,
        volume=1500000.0,
        timestamp=datetime.now(),
    )
    assert data.symbol == "RELIANCE.NS"
    assert data.change_pct == 1.25


def test_market_price_optional_volume():
    """Test MarketPrice with optional volume."""
    from api.schemas import MarketPrice

    data = MarketPrice(
        symbol="BTC-USD",
        price=45000.0,
        change_pct=-2.5,
        timestamp=datetime.now(),
    )
    assert data.volume is None


def test_market_status_schema():
    """Test MarketStatus schema."""
    from api.schemas import MarketStatus

    data = MarketStatus(
        market="nse",
        is_open=True,
        next_close=datetime.now(),
    )
    assert data.is_open is True
    assert data.next_open is None


def test_ws_message_schema():
    """Test WSMessage schema."""
    from api.schemas import WSMessage

    data = WSMessage(
        type="price_update",
        data={"symbol": "RELIANCE.NS", "price": 2550.0},
    )
    assert data.type == "price_update"
    assert data.data["symbol"] == "RELIANCE.NS"
    assert data.timestamp is not None


def test_ws_message_with_custom_timestamp():
    """Test WSMessage with custom timestamp."""
    from api.schemas import WSMessage

    custom_time = datetime(2024, 1, 15, 10, 30, 0)
    data = WSMessage(
        type="trade_executed",
        data={"trade_id": 1, "symbol": "TCS.NS"},
        timestamp=custom_time,
    )
    assert data.timestamp == custom_time
