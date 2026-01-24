"""
Paper Trading Engine for QuantMuse

Provides simulated trading capabilities for crypto and NSE markets.
"""

try:
    from .config import PaperTradingConfig
except ImportError:
    PaperTradingConfig = None

try:
    from .models import PaperSession, PaperPosition, PaperTrade
except ImportError:
    PaperSession = None
    PaperPosition = None
    PaperTrade = None

try:
    from .position_manager import PositionManager
except ImportError:
    PositionManager = None

try:
    from .exit_manager import ExitManager
except ImportError:
    ExitManager = None

try:
    from .executor import PaperExecutor
except ImportError:
    PaperExecutor = None

try:
    from .engine import PaperTradingEngine
except ImportError:
    PaperTradingEngine = None

try:
    from .signal_generator import SignalGenerator, TradingSignal, SignalType
except ImportError:
    SignalGenerator = None
    TradingSignal = None
    SignalType = None

try:
    from .strategy_runner import StrategyRunner
except ImportError:
    StrategyRunner = None

__version__ = "0.1.0"

__all__ = [
    "PaperTradingConfig",
    "PaperSession",
    "PaperPosition",
    "PaperTrade",
    "PositionManager",
    "ExitManager",
    "PaperExecutor",
    "PaperTradingEngine",
    "SignalGenerator",
    "TradingSignal",
    "SignalType",
    "StrategyRunner",
]
