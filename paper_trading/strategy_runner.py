"""Strategy runner for executing strategies and generating signals."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from paper_trading.signal_generator import SignalGenerator, TradingSignal

logger = logging.getLogger(__name__)


class StrategyRunner:
    """Run strategies and collect signals for paper trading."""

    def __init__(
        self,
        signal_generator: Optional[SignalGenerator] = None,
        enabled_strategies: Optional[List[str]] = None,
    ):
        self.signal_generator = signal_generator or SignalGenerator()
        self.enabled_strategies = enabled_strategies or []
        self._strategies = {}

    def register_strategy(self, name: str, strategy: Any) -> None:
        """Register a strategy for execution."""
        self._strategies[name] = strategy
        logger.info(f"Registered strategy: {name}")

    def run_strategy(
        self,
        strategy_name: str,
        symbol: str,
        market: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Run a single strategy on a symbol.

        Args:
            strategy_name: Name of registered strategy
            symbol: Trading symbol
            market: Market type
            data: Market data for analysis

        Returns:
            Strategy output dict or None if error
        """
        if strategy_name not in self._strategies:
            logger.warning(f"Strategy not found: {strategy_name}")
            return None

        strategy = self._strategies[strategy_name]

        try:
            # Run strategy - expects strategy to have an analyze() method
            if hasattr(strategy, "analyze"):
                result = strategy.analyze(symbol, data)
            elif hasattr(strategy, "generate_signal"):
                result = strategy.generate_signal(symbol, data)
            elif callable(strategy):
                result = strategy(symbol, data)
            else:
                logger.error(f"Strategy {strategy_name} has no callable interface")
                return None

            return result
        except Exception as e:
            logger.error(f"Error running strategy {strategy_name} on {symbol}: {e}")
            return None

    def run_all_strategies(
        self,
        symbol: str,
        market: str,
        data: Dict[str, Any],
        current_price: float,
        atr: Optional[float] = None,
    ) -> List[TradingSignal]:
        """
        Run all enabled strategies and generate signals.

        Args:
            symbol: Trading symbol
            market: Market type
            data: Market data
            current_price: Current price
            atr: ATR for dynamic stops

        Returns:
            List of generated trading signals
        """
        signals = []
        strategies_to_run = self.enabled_strategies or list(self._strategies.keys())

        for strategy_name in strategies_to_run:
            result = self.run_strategy(strategy_name, symbol, market, data)

            if result:
                signal = self.signal_generator.generate_signal(
                    symbol=symbol,
                    market=market,
                    strategy_name=strategy_name,
                    strategy_output=result,
                    current_price=current_price,
                    atr=atr,
                )

                if signal:
                    signals.append(signal)
                    logger.info(f"Signal generated: {symbol} {signal.signal_type.value} "
                              f"confidence={signal.confidence:.2f}")

        return signals

    def run_for_watchlist(
        self,
        watchlist: List[str],
        market: str,
        data_provider: callable,
        price_provider: callable,
        atr_provider: Optional[callable] = None,
    ) -> List[TradingSignal]:
        """
        Run strategies for all symbols in a watchlist.

        Args:
            watchlist: List of symbols
            market: Market type
            data_provider: Function to get data for a symbol
            price_provider: Function to get current price
            atr_provider: Optional function to get ATR

        Returns:
            List of all generated signals
        """
        all_signals = []

        for symbol in watchlist:
            try:
                data = data_provider(symbol)
                price = price_provider(symbol)
                atr = atr_provider(symbol) if atr_provider else None

                signals = self.run_all_strategies(
                    symbol=symbol,
                    market=market,
                    data=data,
                    current_price=price,
                    atr=atr,
                )
                all_signals.extend(signals)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

        # Filter and sort signals
        return self.signal_generator.filter_signals(all_signals)
