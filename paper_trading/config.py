"""
Configuration for Paper Trading Engine
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Session-level configuration"""
    initial_balance: float = 1000000.0
    currency: str = "INR"
    execution_mode: str = "auto"  # auto | review | hybrid
    hybrid_confidence_threshold: float = 0.80


@dataclass
class MarketConfig:
    """Per-market configuration"""
    enabled: bool = True
    data_source: str = ""
    poll_interval_minutes: int = 15
    market_open: str = ""
    market_close: str = ""
    timezone: str = "UTC"
    commission_pct: float = 0.1
    watchlist: List[str] = field(default_factory=list)


@dataclass
class SizingConfig:
    """Position sizing configuration"""
    risk_per_trade_pct: float = 1.0
    max_position_pct: float = 20.0
    min_position_value: float = 5000.0
    max_portfolio_exposure_pct: float = 80.0
    use_volatility_adjustment: bool = True
    baseline_atr_pct: float = 2.0


@dataclass
class ExitConfig:
    """Exit rules configuration"""
    default_stop_loss_pct: float = 5.0
    default_take_profit_pct: float = 15.0
    trailing_stop_activation_pct: float = 5.0
    trailing_stop_distance_pct: float = 3.0
    use_atr_stops: bool = True
    atr_stop_multiplier: float = 2.0
    atr_tp_multiplier: float = 3.0


@dataclass
class ConfidenceTier:
    """Confidence tier configuration."""
    min_confidence: float
    sl_factor: float  # Multiplier for stop loss distance (1.0 = original)
    tp_factor: float  # Multiplier for take profit distance
    action: str  # hold, tighten, partial_close, close


@dataclass
class ConfidenceConfig:
    """Confidence-based position management"""
    enable_dynamic_management: bool = True
    recalc_interval_minutes: int = 15
    partial_close_pct: float = 50.0
    min_hold_time_minutes: int = 30
    # Tiers ordered by min_confidence (highest first)
    tiers: List[ConfidenceTier] = field(default_factory=lambda: [
        ConfidenceTier(min_confidence=0.80, sl_factor=1.0, tp_factor=1.0, action="hold"),
        ConfidenceTier(min_confidence=0.60, sl_factor=0.8, tp_factor=0.7, action="tighten"),
        ConfidenceTier(min_confidence=0.40, sl_factor=0.6, tp_factor=0.5, action="partial_close"),
        ConfidenceTier(min_confidence=0.00, sl_factor=0.0, tp_factor=0.0, action="close"),
    ])


@dataclass
class PaperTradingConfig:
    """Master configuration for paper trading"""
    session: SessionConfig = field(default_factory=SessionConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    exits: ExitConfig = field(default_factory=ExitConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    database_url: str = "sqlite:///paper_trading.db"

    # Market configurations
    nse: MarketConfig = field(default_factory=lambda: MarketConfig(
        enabled=True,
        data_source="yfinance",
        poll_interval_minutes=15,
        market_open="09:15",
        market_close="15:30",
        timezone="Asia/Kolkata",
        commission_pct=0.02,
        watchlist=[
            "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS",
            "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
            "KOTAKBANK.NS", "ITC.NS", "SBIN.NS"
        ]
    ))

    crypto: MarketConfig = field(default_factory=lambda: MarketConfig(
        enabled=True,
        data_source="binance",
        poll_interval_minutes=1,
        market_open="00:00",
        market_close="23:59",
        timezone="UTC",
        commission_pct=0.1,
        watchlist=[
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"
        ]
    ))

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PaperTradingConfig":
        """Create config from dictionary with overrides"""
        config = cls()

        if "session" in config_dict:
            for key, value in config_dict["session"].items():
                if hasattr(config.session, key):
                    setattr(config.session, key, value)

        if "sizing" in config_dict:
            for key, value in config_dict["sizing"].items():
                if hasattr(config.sizing, key):
                    setattr(config.sizing, key, value)

        if "exits" in config_dict:
            for key, value in config_dict["exits"].items():
                if hasattr(config.exits, key):
                    setattr(config.exits, key, value)

        if "database_url" in config_dict:
            config.database_url = config_dict["database_url"]

        return config
