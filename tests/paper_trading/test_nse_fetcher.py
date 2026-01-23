"""Tests for NSE data fetcher using yfinance"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from data_service.fetchers.nse_fetcher import NSEFetcher


class TestNSEFetcher(unittest.TestCase):
    """Test NSE fetcher with mocked yfinance"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = NSEFetcher()

        # Sample OHLCV data
        dates = pd.date_range(start="2026-01-01", periods=5, freq="D")
        self.mock_df = pd.DataFrame({
            "Open": [2400.0, 2420.0, 2450.0, 2440.0, 2460.0],
            "High": [2430.0, 2460.0, 2480.0, 2470.0, 2490.0],
            "Low": [2390.0, 2410.0, 2440.0, 2430.0, 2450.0],
            "Close": [2420.0, 2450.0, 2470.0, 2460.0, 2480.0],
            "Volume": [1000000, 1100000, 1200000, 1150000, 1250000],
        }, index=dates)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_fetch_historical_data(self, mock_yf):
        """Test fetching historical OHLCV data"""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = self.mock_df
        mock_yf.Ticker.return_value = mock_ticker

        df = self.fetcher.fetch_historical_data("RELIANCE.NS", interval="1d")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)
        self.assertIn("open", df.columns)
        self.assertIn("close", df.columns)
        self.assertIn("volume", df.columns)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_get_current_price(self, mock_yf):
        """Test getting current price"""
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 2480.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = self.fetcher.get_current_price("RELIANCE.NS")

        self.assertEqual(price, 2480.0)

    @patch("data_service.fetchers.nse_fetcher.yf")
    def test_get_current_price_fallback(self, mock_yf):
        """Test current price fallback to fast_info"""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.fast_info = {"lastPrice": 2475.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = self.fetcher.get_current_price("RELIANCE.NS")

        self.assertEqual(price, 2475.0)

    def test_normalize_symbol(self):
        """Test symbol normalization for NSE"""
        # Should add .NS if missing
        self.assertEqual(self.fetcher.normalize_symbol("RELIANCE"), "RELIANCE.NS")
        # Should keep .NS if present
        self.assertEqual(self.fetcher.normalize_symbol("RELIANCE.NS"), "RELIANCE.NS")
        # Should handle lowercase
        self.assertEqual(self.fetcher.normalize_symbol("reliance"), "RELIANCE.NS")

    def test_is_market_open_returns_bool(self):
        """Test market open check returns boolean"""
        result = self.fetcher.is_market_open()
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
