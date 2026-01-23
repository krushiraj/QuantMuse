"""
Position Manager for Paper Trading

Handles position sizing, risk management, and signal validation.
"""
import logging
from typing import Tuple, List, Dict, Any, Optional

from .config import PaperTradingConfig

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manages position sizing and risk controls.

    Features:
    - Risk-based position sizing
    - Volatility adjustment
    - Portfolio exposure limits
    - Signal validation
    """

    def __init__(self, config: PaperTradingConfig):
        """
        Initialize position manager.

        Args:
            config: Paper trading configuration
        """
        self.config = config
        self.sizing = config.sizing
        self.logger = logging.getLogger(__name__)

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: float,
        volatility_factor: float = 1.0,
    ) -> int:
        """
        Calculate position size based on risk per trade.

        Formula: Position Size = (Portfolio * Risk%) / (Entry * Stop Distance * Vol Factor)

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            volatility_factor: Volatility adjustment factor (>1 = reduce size)

        Returns:
            Number of shares/units to buy (integer)
        """
        if entry_price <= 0 or stop_loss <= 0:
            self.logger.error("Invalid entry or stop loss price")
            return 0

        # Calculate stop distance as percentage
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price

        if stop_distance_pct == 0:
            self.logger.error("Stop loss equals entry price")
            return 0

        # Risk amount
        risk_amount = portfolio_value * (self.sizing.risk_per_trade_pct / 100)

        # Apply volatility adjustment
        adjusted_risk = risk_amount / max(volatility_factor, 0.1)

        # Calculate position size
        position_value = adjusted_risk / stop_distance_pct
        shares = position_value / entry_price

        # Apply max position constraint
        max_position_value = portfolio_value * (self.sizing.max_position_pct / 100)
        max_shares = max_position_value / entry_price
        shares = min(shares, max_shares)

        # Apply min position constraint
        min_shares = self.sizing.min_position_value / entry_price
        if shares < min_shares:
            # Check if we can afford min position
            if self.sizing.min_position_value <= portfolio_value * (self.sizing.max_position_pct / 100):
                shares = min_shares
            else:
                shares = 0

        # Round down to integer
        return int(shares)

    def calculate_volatility_factor(self, atr_pct: float) -> float:
        """
        Calculate volatility adjustment factor.

        Factor > 1.0 means high volatility (reduce position)
        Factor < 1.0 means low volatility (increase position)

        Args:
            atr_pct: Asset's ATR as percentage of price

        Returns:
            Volatility factor
        """
        if not self.sizing.use_volatility_adjustment:
            return 1.0

        baseline = self.sizing.baseline_atr_pct
        if baseline <= 0:
            return 1.0

        factor = atr_pct / baseline

        # Clamp to reasonable range
        factor = max(0.25, min(factor, 4.0))

        return factor

    def check_exposure_limit(
        self,
        portfolio_value: float,
        current_invested: float,
        new_position_value: float,
    ) -> bool:
        """
        Check if adding a new position would exceed exposure limit.

        Args:
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount
            new_position_value: Value of new position to add

        Returns:
            True if position can be added, False otherwise
        """
        max_exposure = portfolio_value * (self.sizing.max_portfolio_exposure_pct / 100)
        new_total = current_invested + new_position_value

        return new_total <= max_exposure

    def get_available_capital(
        self,
        portfolio_value: float,
        current_invested: float,
    ) -> float:
        """
        Get available capital for new positions.

        Args:
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount

        Returns:
            Available capital for new positions
        """
        max_exposure = portfolio_value * (self.sizing.max_portfolio_exposure_pct / 100)
        return max(0, max_exposure - current_invested)

    def validate_signal(
        self,
        signal: Dict[str, Any],
        portfolio_value: float,
        current_invested: float,
        open_positions: List[str],
    ) -> Tuple[bool, str]:
        """
        Validate if a signal can be executed.

        Args:
            signal: Signal dictionary with symbol, entry_price, stop_loss, confidence
            portfolio_value: Total portfolio value
            current_invested: Currently invested amount
            open_positions: List of symbols with open positions

        Returns:
            Tuple of (is_valid, reason)
        """
        symbol = signal.get("symbol", "")
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        confidence = signal.get("confidence", 0)

        # Check if already in position
        if symbol in open_positions:
            return False, f"Already in position for {symbol}"

        # Check confidence threshold
        min_confidence = 0.6
        if confidence < min_confidence:
            return False, f"Confidence {confidence} below threshold {min_confidence}"

        # Check exposure limit
        position_size = self.calculate_position_size(
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            stop_loss=stop_loss,
        )
        position_value = position_size * entry_price

        if not self.check_exposure_limit(portfolio_value, current_invested, position_value):
            return False, f"Would exceed max exposure limit"

        # Check if position is valid
        if position_size <= 0:
            return False, "Position size would be zero or negative"

        return True, "Signal validated"

    def calculate_commission(
        self,
        value: float,
        market: str,
    ) -> float:
        """
        Calculate commission for a trade.

        Args:
            value: Trade value
            market: Market identifier (nse, crypto)

        Returns:
            Commission amount
        """
        if market == "nse":
            rate = self.config.nse.commission_pct
        elif market == "crypto":
            rate = self.config.crypto.commission_pct
        else:
            rate = 0.1  # Default 0.1%

        return value * (rate / 100)
