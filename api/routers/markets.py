"""Markets router for market data and prices."""
from typing import List, Optional
from datetime import datetime
import logging
from fastapi import APIRouter, Query

from api.schemas import MarketPrice, MarketStatus

router = APIRouter(prefix="/api/markets", tags=["markets"])
logger = logging.getLogger(__name__)

# Default watchlists
DEFAULT_NSE_WATCHLIST = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS",
    "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "ITC.NS", "SBIN.NS"
]

DEFAULT_CRYPTO_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"
]

# Crypto symbol suffixes
CRYPTO_SUFFIXES = ("USDT", "BUSD", "BTC", "ETH", "BNB")


def is_crypto_symbol(symbol: str) -> bool:
    """Check if a symbol is a crypto trading pair."""
    return any(symbol.upper().endswith(suffix) for suffix in CRYPTO_SUFFIXES)


def get_crypto_price(symbol: str) -> float:
    """Get current price for a crypto symbol using Binance API."""
    try:
        from binance.client import Client
        client = Client(tld='us')
        ticker = client.get_symbol_ticker(symbol=symbol.upper())
        return float(ticker['price'])
    except Exception as e:
        logger.warning(f"Failed to get crypto price for {symbol}: {e}")
        return 0.0


@router.get("/status")
def get_market_status():
    """Get current market status for all markets."""
    from data_service.fetchers.nse_fetcher import NSEFetcher

    nse_fetcher = NSEFetcher()
    nse_is_open = nse_fetcher.is_market_open()

    return {
        "nse": {
            "market": "nse",
            "is_open": nse_is_open,
            "hours": "9:15 AM - 3:30 PM IST",
            "timezone": "Asia/Kolkata",
        },
        "crypto": {
            "market": "crypto",
            "is_open": True,  # Crypto is always open
            "hours": "24/7",
            "timezone": "UTC",
        }
    }


@router.get("/prices", response_model=List[MarketPrice])
def get_prices(
    symbols: str = Query(..., description="Comma-separated list of symbols")
):
    """Get current prices for specified symbols."""
    from data_service.fetchers.nse_fetcher import NSEFetcher

    symbol_list = [s.strip() for s in symbols.split(",")]
    nse_fetcher = NSEFetcher()

    prices = []
    for symbol in symbol_list:
        try:
            if is_crypto_symbol(symbol):
                price = get_crypto_price(symbol)
            else:
                price = nse_fetcher.get_current_price(symbol)

            prices.append(MarketPrice(
                symbol=symbol,
                price=price,
                change_pct=0.0,  # Placeholder
                timestamp=datetime.now()
            ))
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
            continue

    return prices


@router.get("/watchlist")
def get_watchlist():
    """Get default watchlists for each market."""
    return {
        "nse": DEFAULT_NSE_WATCHLIST,
        "crypto": DEFAULT_CRYPTO_WATCHLIST,
    }


@router.get("/quote/{symbol}")
def get_quote(symbol: str):
    """Get detailed quote for a symbol."""
    from data_service.fetchers.nse_fetcher import NSEFetcher

    try:
        if is_crypto_symbol(symbol):
            price = get_crypto_price(symbol)
            # For crypto, approximate ATR using recent volatility
            atr = price * 0.02  # Estimate 2% ATR for crypto
        else:
            nse_fetcher = NSEFetcher()
            price = nse_fetcher.get_current_price(symbol)
            atr = nse_fetcher.calculate_atr(symbol)

        return {
            "symbol": symbol,
            "price": price,
            "atr": atr,
            "atr_pct": (atr / price * 100) if price > 0 else 0,
            "timestamp": datetime.now(),
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "error": str(e),
        }
