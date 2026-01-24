"""Tests for alert system."""
import pytest
from paper_trading.alerts import AlertManager, AlertType, AlertPriority, Alert


@pytest.fixture
def manager():
    """Create fresh alert manager."""
    return AlertManager(max_alerts=10)


def test_create_alert(manager):
    """Test creating an alert."""
    alert = manager.create_alert(
        AlertType.SIGNAL_GENERATED,
        "Test Alert",
        "Test message",
        priority=AlertPriority.HIGH,
        session_id=1,
    )

    assert alert.id is not None
    assert alert.title == "Test Alert"
    assert alert.priority == AlertPriority.HIGH
    assert not alert.read


def test_get_alerts(manager):
    """Test getting alerts."""
    manager.create_alert(AlertType.SIGNAL_GENERATED, "A", "msg", session_id=1)
    manager.create_alert(AlertType.TRADE_EXECUTED, "B", "msg", session_id=1)
    manager.create_alert(AlertType.SIGNAL_GENERATED, "C", "msg", session_id=2)

    # Get all
    alerts = manager.get_alerts()
    assert len(alerts) == 3

    # Filter by session
    alerts = manager.get_alerts(session_id=1)
    assert len(alerts) == 2

    # Filter by type
    alerts = manager.get_alerts(alert_type=AlertType.SIGNAL_GENERATED)
    assert len(alerts) == 2


def test_mark_read(manager):
    """Test marking alerts as read."""
    alert = manager.create_alert(AlertType.SIGNAL_GENERATED, "Test", "msg")
    assert not alert.read

    manager.mark_read(alert.id)
    assert alert.read


def test_unread_filter(manager):
    """Test unread filter."""
    a1 = manager.create_alert(AlertType.SIGNAL_GENERATED, "A", "msg")
    a2 = manager.create_alert(AlertType.TRADE_EXECUTED, "B", "msg")

    manager.mark_read(a1.id)

    unread = manager.get_alerts(unread_only=True)
    assert len(unread) == 1
    assert unread[0].id == a2.id


def test_max_alerts(manager):
    """Test max alerts limit."""
    for i in range(15):
        manager.create_alert(AlertType.SIGNAL_GENERATED, f"Alert {i}", "msg")

    assert len(manager.alerts) == 10  # max_alerts


def test_convenience_methods(manager):
    """Test convenience alert methods."""
    alert = manager.signal_generated(1, "RELIANCE.NS", "BUY", 0.85, "MomentumStrategy")
    assert alert.alert_type == AlertType.SIGNAL_GENERATED
    assert "RELIANCE.NS" in alert.title

    alert = manager.trade_executed(1, "TCS.NS", "buy", 100, 3500.0)
    assert alert.alert_type == AlertType.TRADE_EXECUTED

    alert = manager.stop_loss_hit(1, "INFY.NS", 1500.0, 1425.0, -7500.0)
    assert alert.alert_type == AlertType.STOP_LOSS_HIT
    assert alert.priority == AlertPriority.CRITICAL


def test_handler_registration(manager):
    """Test alert handler registration."""
    received = []

    def handler(alert):
        received.append(alert)

    manager.register_handler(AlertType.SIGNAL_GENERATED, handler)
    manager.create_alert(AlertType.SIGNAL_GENERATED, "Test", "msg")
    manager.create_alert(AlertType.TRADE_EXECUTED, "Other", "msg")

    assert len(received) == 1
    assert received[0].title == "Test"
