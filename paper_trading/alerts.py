"""Alert system for paper trading notifications."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts."""
    SIGNAL_GENERATED = "signal_generated"
    TRADE_EXECUTED = "trade_executed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    TRAILING_STOP_HIT = "trailing_stop_hit"
    CONFIDENCE_CHANGE = "confidence_change"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    DAILY_SUMMARY = "daily_summary"
    ERROR = "error"


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Alert:
    """Alert notification."""
    id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[int] = None
    read: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.alert_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "read": self.read,
        }


class AlertManager:
    """Manage alerts and notifications."""

    def __init__(self, max_alerts: int = 100):
        self.alerts: List[Alert] = []
        self.max_alerts = max_alerts
        self.handlers: Dict[AlertType, List[Callable]] = {}
        self._alert_counter = 0

    def _generate_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"alert_{self._alert_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def register_handler(self, alert_type: AlertType, handler: Callable) -> None:
        """Register a handler for an alert type."""
        if alert_type not in self.handlers:
            self.handlers[alert_type] = []
        self.handlers[alert_type].append(handler)

    def create_alert(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
        session_id: Optional[int] = None,
    ) -> Alert:
        """Create and dispatch an alert."""
        alert = Alert(
            id=self._generate_id(),
            alert_type=alert_type,
            priority=priority,
            title=title,
            message=message,
            data=data or {},
            session_id=session_id,
        )

        # Add to list (maintain max size)
        self.alerts.insert(0, alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[:self.max_alerts]

        # Dispatch to handlers
        self._dispatch(alert)

        logger.info(f"Alert created: [{alert.priority.name}] {alert.title}")
        return alert

    def _dispatch(self, alert: Alert) -> None:
        """Dispatch alert to registered handlers."""
        handlers = self.handlers.get(alert.alert_type, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def get_alerts(
        self,
        session_id: Optional[int] = None,
        alert_type: Optional[AlertType] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        filtered = self.alerts

        if session_id is not None:
            filtered = [a for a in filtered if a.session_id == session_id]
        if alert_type is not None:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        if unread_only:
            filtered = [a for a in filtered if not a.read]

        return filtered[:limit]

    def mark_read(self, alert_id: str) -> bool:
        """Mark an alert as read."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.read = True
                return True
        return False

    def mark_all_read(self, session_id: Optional[int] = None) -> int:
        """Mark all alerts as read."""
        count = 0
        for alert in self.alerts:
            if session_id is None or alert.session_id == session_id:
                if not alert.read:
                    alert.read = True
                    count += 1
        return count

    def clear_alerts(self, session_id: Optional[int] = None) -> int:
        """Clear alerts."""
        if session_id is None:
            count = len(self.alerts)
            self.alerts = []
        else:
            original = len(self.alerts)
            self.alerts = [a for a in self.alerts if a.session_id != session_id]
            count = original - len(self.alerts)
        return count

    # Convenience methods for common alerts
    def signal_generated(
        self,
        session_id: int,
        symbol: str,
        signal_type: str,
        confidence: float,
        strategy: str,
    ) -> Alert:
        """Create alert for new signal."""
        return self.create_alert(
            AlertType.SIGNAL_GENERATED,
            f"New {signal_type} Signal: {symbol}",
            f"{strategy} generated {signal_type} signal for {symbol} with {confidence:.0%} confidence",
            priority=AlertPriority.HIGH if confidence > 0.8 else AlertPriority.MEDIUM,
            data={"symbol": symbol, "signal_type": signal_type, "confidence": confidence, "strategy": strategy},
            session_id=session_id,
        )

    def trade_executed(
        self,
        session_id: int,
        symbol: str,
        trade_type: str,
        quantity: int,
        price: float,
        pnl: Optional[float] = None,
    ) -> Alert:
        """Create alert for executed trade."""
        msg = f"Executed {trade_type.upper()} {quantity} {symbol} @ ₹{price:,.2f}"
        if pnl is not None:
            msg += f" (P&L: {'+'if pnl >= 0 else ''}₹{pnl:,.2f})"

        return self.create_alert(
            AlertType.TRADE_EXECUTED,
            f"Trade Executed: {symbol}",
            msg,
            priority=AlertPriority.HIGH,
            data={"symbol": symbol, "trade_type": trade_type, "quantity": quantity, "price": price, "pnl": pnl},
            session_id=session_id,
        )

    def stop_loss_hit(
        self,
        session_id: int,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
    ) -> Alert:
        """Create alert for stop loss hit."""
        return self.create_alert(
            AlertType.STOP_LOSS_HIT,
            f"Stop Loss Hit: {symbol}",
            f"{symbol} hit stop loss at ₹{exit_price:,.2f} (Entry: ₹{entry_price:,.2f}, Loss: ₹{abs(pnl):,.2f})",
            priority=AlertPriority.CRITICAL,
            data={"symbol": symbol, "entry_price": entry_price, "exit_price": exit_price, "pnl": pnl},
            session_id=session_id,
        )

    def take_profit_hit(
        self,
        session_id: int,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
    ) -> Alert:
        """Create alert for take profit hit."""
        return self.create_alert(
            AlertType.TAKE_PROFIT_HIT,
            f"Take Profit Hit: {symbol}",
            f"{symbol} hit take profit at ₹{exit_price:,.2f} (Entry: ₹{entry_price:,.2f}, Profit: ₹{pnl:,.2f})",
            priority=AlertPriority.HIGH,
            data={"symbol": symbol, "entry_price": entry_price, "exit_price": exit_price, "pnl": pnl},
            session_id=session_id,
        )

    def daily_summary(
        self,
        session_id: int,
        portfolio_value: float,
        daily_pnl: float,
        open_positions: int,
        trades_today: int,
    ) -> Alert:
        """Create daily summary alert."""
        return self.create_alert(
            AlertType.DAILY_SUMMARY,
            "Daily Summary",
            f"Portfolio: ₹{portfolio_value:,.0f} | Today: {'+'if daily_pnl >= 0 else ''}₹{daily_pnl:,.0f} | "
            f"Positions: {open_positions} | Trades: {trades_today}",
            priority=AlertPriority.LOW,
            data={
                "portfolio_value": portfolio_value,
                "daily_pnl": daily_pnl,
                "open_positions": open_positions,
                "trades_today": trades_today,
            },
            session_id=session_id,
        )


# Global alert manager instance
alert_manager = AlertManager()
