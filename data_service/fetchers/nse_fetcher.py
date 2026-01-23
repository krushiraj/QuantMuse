"""
NSE Data Fetcher using yfinance

Fetches historical and current price data for NSE (Indian) stocks.
Uses Yahoo Finance with .NS suffix for NSE symbols.
"""
import logging
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

# NSE market hours
IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


class NSEFetcher:
    """
    Fetcher for NSE (National Stock Exchange of India) data via yfinance.

    Supports:
    - Historical OHLCV data
    - Current prices
    - Market hours detection
    """

    TIMEFRAME_MAP = {
        "1d": "1d",
        "1h": "1h",
        "15m": "15m",
        "5m": "5m",
    }

    def __init__(self):
        """Initialize NSE fetcher"""
        self.logger = logging.getLogger(__name__)

        if yf is None:
            self.logger.error("yfinance not installed. Run: pip install yfinance")
            raise ImportError("yfinance is required for NSEFetcher")

        self.logger.info("NSEFetcher initialized")

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to NSE format (add .NS suffix if missing)

        Args:
            symbol: Stock symbol (e.g., "RELIANCE" or "RELIANCE.NS")

        Returns:
            Normalized symbol with .NS suffix
        """
        symbol = symbol.upper().strip()
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
        return symbol

    def fetch_historical_data(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        period: str = "1mo",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an NSE stock.

        Args:
            symbol: NSE stock symbol (e.g., "RELIANCE.NS" or "RELIANCE")
            interval: Data interval (1d, 1h, 15m, 5m)
            start_time: Start datetime (optional, uses period if not specified)
            end_time: End datetime (optional, defaults to now)
            period: Period to fetch if start_time not specified (1d, 5d, 1mo, 3mo, 1y)

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        symbol = self.normalize_symbol(symbol)
        yf_interval = self.TIMEFRAME_MAP.get(interval, "1d")

        try:
            ticker = yf.Ticker(symbol)

            if start_time and end_time:
                df = ticker.history(
                    start=start_time.strftime("%Y-%m-%d"),
                    end=end_time.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                )
            elif start_time:
                df = ticker.history(
                    start=start_time.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                )
            else:
                df = ticker.history(period=period, interval=yf_interval)

            if df.empty:
                self.logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()

            # Keep only OHLCV columns
            columns_to_keep = ["open", "high", "low", "close", "volume"]
            available_columns = [col for col in columns_to_keep if col in df.columns]
            df = df[available_columns]

            self.logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise

    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for an NSE stock.

        Args:
            symbol: NSE stock symbol

        Returns:
            Current price as float
        """
        symbol = self.normalize_symbol(symbol)

        try:
            ticker = yf.Ticker(symbol)

            # Try regularMarketPrice first
            price = ticker.info.get("regularMarketPrice")

            # Fallback to fast_info
            if price is None:
                price = ticker.fast_info.get("lastPrice", 0)

            if price is None or price == 0:
                # Final fallback: get last close from history
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
                else:
                    price = 0.0

            return float(price)

        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {str(e)}")
            return 0.0

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.

        Args:
            symbols: List of NSE stock symbols

        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
        return prices

    def is_market_open(self) -> bool:
        """
        Check if NSE market is currently open.

        Returns:
            True if market is open (weekday, between 9:15 AM - 3:30 PM IST)
        """
        now = datetime.now(IST)

        # Check if weekday (0=Monday, 6=Sunday)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        current_time = now.time()
        return MARKET_OPEN <= current_time <= MARKET_CLOSE

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get detailed market status.

        Returns:
            Dictionary with market status information
        """
        now = datetime.now(IST)
        is_open = self.is_market_open()

        return {
            "is_open": is_open,
            "current_time": now.strftime("%H:%M:%S"),
            "timezone": "Asia/Kolkata",
            "market_open": MARKET_OPEN.strftime("%H:%M"),
            "market_close": MARKET_CLOSE.strftime("%H:%M"),
            "day_of_week": now.strftime("%A"),
        }

    def calculate_atr(
        self,
        symbol: str,
        period: int = 14,
        interval: str = "1d",
    ) -> float:
        """
        Calculate Average True Range for volatility-based position sizing.

        Args:
            symbol: NSE stock symbol
            period: ATR period (default 14)
            interval: Data interval

        Returns:
            ATR value
        """
        df = self.fetch_historical_data(symbol, interval=interval, period="3mo")

        if len(df) < period + 1:
            self.logger.warning(f"Insufficient data for ATR calculation: {symbol}")
            return 0.0

        # Calculate True Range
        df["prev_close"] = df["close"].shift(1)
        df["tr1"] = df["high"] - df["low"]
        df["tr2"] = abs(df["high"] - df["prev_close"])
        df["tr3"] = abs(df["low"] - df["prev_close"])
        df["true_range"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

        # Calculate ATR
        atr = df["true_range"].rolling(window=period).mean().iloc[-1]

        return float(atr)
