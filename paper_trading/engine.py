"""
Paper Trading Engine

Main orchestrator for the paper trading system.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import PaperTradingConfig
from .models import (
    PaperSession, PaperPosition, PaperTrade, PendingSignal,
    DailyPerformance, create_engine_and_tables
)
from .position_manager import PositionManager
from .exit_manager import ExitManager, ExitSignal
from .executor import PaperExecutor

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Main paper trading engine.

    Orchestrates:
    - Session management
    - Signal processing
    - Position monitoring
    - Exit checking
    - Performance tracking
    """

    def __init__(
        self,
        config: PaperTradingConfig,
        db_engine=None,
    ):
        """
        Initialize paper trading engine.

        Args:
            config: Paper trading configuration
            db_engine: Optional SQLAlchemy engine (creates new if not provided)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize database
        if db_engine is None:
            db_engine = create_engine(config.database_url)
            create_engine_and_tables(db_engine)

        self.db_engine = db_engine
        self.Session = sessionmaker(bind=db_engine)

        # Initialize managers
        self.position_manager = PositionManager(config)
        self.exit_manager = ExitManager(config)

        # Initialize fetchers (lazy loaded)
        self._nse_fetcher = None
        self._binance_fetcher = None

        self.logger.info("PaperTradingEngine initialized")

    @property
    def nse_fetcher(self):
        """Lazy load NSE fetcher"""
        if self._nse_fetcher is None:
            try:
                from data_service.fetchers.nse_fetcher import NSEFetcher
                self._nse_fetcher = NSEFetcher()
            except ImportError:
                self.logger.warning("NSEFetcher not available")
        return self._nse_fetcher

    @property
    def binance_fetcher(self):
        """Lazy load Binance fetcher"""
        if self._binance_fetcher is None:
            try:
                from data_service.fetchers.binance_fetcher import BinanceFetcher
                self._binance_fetcher = BinanceFetcher()
            except ImportError:
                self.logger.warning("BinanceFetcher not available")
        return self._binance_fetcher

    def get_db(self) -> Session:
        """Get a new database session"""
        return self.Session()

    def create_session(
        self,
        name: str,
        initial_balance: Optional[float] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> PaperSession:
        """
        Create a new paper trading session.

        Args:
            name: Session name
            initial_balance: Starting balance (uses config default if not specified)
            config_overrides: Optional config overrides for this session

        Returns:
            Created PaperSession
        """
        db = self.get_db()
        try:
            balance = initial_balance or self.config.session.initial_balance

            session = PaperSession(
                name=name,
                initial_balance=balance,
                current_balance=balance,
                currency=self.config.session.currency,
                status="active",
                config_json=str(config_overrides) if config_overrides else None,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            self.logger.info(f"Created session: {name} with balance {balance}")
            return session
        finally:
            db.close()

    def get_current_price(self, symbol: str, market: str) -> float:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol
            market: Market identifier (nse, crypto)

        Returns:
            Current price
        """
        if market == "nse" and self.nse_fetcher:
            return self.nse_fetcher.get_current_price(symbol)
        elif market == "crypto" and self.binance_fetcher:
            return self.binance_fetcher.get_current_price(symbol)
        else:
            self.logger.warning(f"No fetcher available for {market}")
            return 0.0

    def get_atr(self, symbol: str, market: str) -> float:
        """
        Get ATR for volatility-based sizing.

        Args:
            symbol: Trading symbol
            market: Market identifier

        Returns:
            ATR value
        """
        if market == "nse" and self.nse_fetcher:
            return self.nse_fetcher.calculate_atr(symbol)
        return 0.0

    def process_signal(
        self,
        session_id: int,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a trading signal.

        Args:
            session_id: Paper trading session ID
            signal: Signal dictionary

        Returns:
            Result dictionary with execution details
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)

            session = db.query(PaperSession).filter_by(id=session_id).first()
            if not session:
                return {"executed": False, "reason": "Session not found"}

            # Get current positions
            open_positions = executor.get_open_positions(session_id)
            open_symbols = [p.symbol for p in open_positions]

            # Get session value
            session_value = executor.get_session_value(session_id)

            # Validate signal
            is_valid, reason = self.position_manager.validate_signal(
                signal=signal,
                portfolio_value=session_value["total"],
                current_invested=session_value["invested"],
                open_positions=open_symbols,
            )

            if not is_valid:
                return {"executed": False, "reason": reason}

            # Calculate position size
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)
            market = signal.get("market", "nse")
            symbol = signal.get("symbol", "")

            # Get ATR for volatility adjustment
            atr = self.get_atr(symbol, market)
            atr_pct = (atr / entry_price * 100) if entry_price > 0 and atr > 0 else self.config.sizing.baseline_atr_pct
            volatility_factor = self.position_manager.calculate_volatility_factor(atr_pct)

            quantity = self.position_manager.calculate_position_size(
                portfolio_value=session_value["total"],
                entry_price=entry_price,
                stop_loss=stop_loss,
                volatility_factor=volatility_factor,
            )

            if quantity <= 0:
                return {"executed": False, "reason": "Position size is zero"}

            # Check execution mode
            exec_mode = self.config.session.execution_mode
            confidence = signal.get("confidence", 0)

            if exec_mode == "review":
                # Queue for review
                pending = PendingSignal(
                    session_id=session_id,
                    symbol=symbol,
                    market=market,
                    signal_type=signal.get("direction", "long"),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=signal.get("take_profit"),
                    confidence=confidence,
                    strategy=signal.get("strategy", ""),
                    status="pending",
                )
                db.add(pending)
                db.commit()
                return {"executed": False, "reason": "Queued for review", "signal_id": pending.id}

            elif exec_mode == "hybrid":
                if confidence < self.config.session.hybrid_confidence_threshold:
                    # Queue low-confidence signals
                    pending = PendingSignal(
                        session_id=session_id,
                        symbol=symbol,
                        market=market,
                        signal_type=signal.get("direction", "long"),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=signal.get("take_profit"),
                        confidence=confidence,
                        strategy=signal.get("strategy", ""),
                        status="pending",
                    )
                    db.add(pending)
                    db.commit()
                    return {"executed": False, "reason": "Low confidence, queued for review", "signal_id": pending.id}

            # Execute trade (auto mode or high-confidence hybrid)
            position = executor.open_position(
                session_id=session_id,
                signal=signal,
                quantity=quantity,
            )

            return {
                "executed": True,
                "position_id": position.id,
                "symbol": position.symbol,
                "quantity": quantity,
                "entry_price": entry_price,
            }

        finally:
            db.close()

    def check_exits(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Check all open positions for exit conditions.

        Args:
            session_id: Paper trading session ID

        Returns:
            List of exit signals triggered
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)
            open_positions = executor.get_open_positions(session_id)

            exits_triggered = []

            for position in open_positions:
                # Get current price
                current_price = self.get_current_price(position.symbol, position.market)
                if current_price <= 0:
                    continue

                # Update position price
                executor.update_position_price(position.id, current_price)

                # Build position dict for exit check
                pos_dict = {
                    "entry_price": position.entry_price,
                    "current_price": current_price,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "trailing_stop": position.trailing_stop,
                    "trailing_stop_high": position.trailing_stop_high,
                    "direction": position.direction,
                }

                # Update trailing stop
                pos_dict = self.exit_manager.update_trailing_stop(pos_dict)
                if pos_dict.get("trailing_stop") != position.trailing_stop:
                    position.trailing_stop = pos_dict["trailing_stop"]
                    position.trailing_stop_high = pos_dict.get("trailing_stop_high")
                    db.commit()

                # Check for exit
                exit_signal = self.exit_manager.check_exit(pos_dict)

                if exit_signal and exit_signal.should_exit:
                    # Execute exit
                    executor.close_position(
                        position_id=position.id,
                        exit_price=current_price,
                        reason=exit_signal.reason,
                    )

                    exits_triggered.append({
                        "position_id": position.id,
                        "symbol": position.symbol,
                        "reason": exit_signal.reason,
                        "exit_price": current_price,
                        "pnl_pct": exit_signal.pnl_pct,
                    })

            return exits_triggered

        finally:
            db.close()

    def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        """
        Get summary of a trading session.

        Args:
            session_id: Paper trading session ID

        Returns:
            Summary dictionary
        """
        db = self.get_db()
        try:
            executor = PaperExecutor(self.config, db)

            session = db.query(PaperSession).filter_by(id=session_id).first()
            if not session:
                return {}

            session_value = executor.get_session_value(session_id)
            open_positions = executor.get_open_positions(session_id)

            # Calculate P&L
            total_pnl = session_value["total"] - session.initial_balance
            total_pnl_pct = (total_pnl / session.initial_balance) * 100

            # Count trades
            total_trades = db.query(PaperTrade).filter_by(session_id=session_id).count()
            winning_trades = db.query(PaperTrade).filter(
                PaperTrade.session_id == session_id,
                PaperTrade.pnl > 0
            ).count()

            return {
                "session_id": session_id,
                "session_name": session.name,
                "status": session.status,
                "initial_balance": session.initial_balance,
                "current_balance": session.current_balance,
                "cash_available": session_value["cash"],
                "invested_value": session_value["invested"],
                "total_value": session_value["total"],
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "num_open_positions": len(open_positions),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }

        finally:
            db.close()
