"""Binance WebSocket client for real-time price streaming."""
import asyncio
import json
import logging
from typing import Dict, Callable, Optional, List, Set
from datetime import datetime

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """WebSocket client for Binance real-time price feeds."""

    STREAM_URL = "wss://stream.binance.com:9443/ws"
    STREAM_URL_COMBINED = "wss://stream.binance.com:9443/stream"

    def __init__(self):
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package required: pip install websockets")

        self.websocket = None
        self.subscriptions: Set[str] = set()
        self.callbacks: Dict[str, List[Callable]] = {}
        self.prices: Dict[str, float] = {}
        self.running = False
        self._reconnect_delay = 1

    def _get_stream_name(self, symbol: str, stream_type: str = "ticker") -> str:
        """Get stream name for a symbol."""
        symbol_lower = symbol.lower()
        if stream_type == "ticker":
            return f"{symbol_lower}@ticker"
        elif stream_type == "trade":
            return f"{symbol_lower}@trade"
        elif stream_type == "kline":
            return f"{symbol_lower}@kline_1m"
        return f"{symbol_lower}@ticker"

    async def connect(self, symbols: List[str]) -> None:
        """
        Connect to Binance WebSocket and subscribe to symbols.

        Args:
            symbols: List of trading pairs (e.g., ["BTCUSDT", "ETHUSDT"])
        """
        if not symbols:
            return

        streams = [self._get_stream_name(s) for s in symbols]
        stream_param = "/".join(streams)
        url = f"{self.STREAM_URL_COMBINED}?streams={stream_param}"

        self.running = True
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    self.websocket = ws
                    self._reconnect_delay = 1
                    logger.info(f"Connected to Binance WebSocket for {len(symbols)} symbols")

                    self.subscriptions = set(symbols)

                    async for message in ws:
                        await self._handle_message(message)

            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                if self.running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)

            # Combined stream format: {"stream": "btcusdt@ticker", "data": {...}}
            if "stream" in data:
                stream = data["stream"]
                payload = data["data"]
            else:
                payload = data
                stream = None

            # Handle ticker data
            if "e" in payload and payload["e"] == "24hrTicker":
                symbol = payload["s"]  # e.g., "BTCUSDT"
                price = float(payload["c"])  # Current price

                self.prices[symbol] = price

                # Call registered callbacks
                if symbol in self.callbacks:
                    for callback in self.callbacks[symbol]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(symbol, price, payload)
                            else:
                                callback(symbol, price, payload)
                        except Exception as e:
                            logger.error(f"Callback error for {symbol}: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def register_callback(self, symbol: str, callback: Callable) -> None:
        """
        Register a callback for price updates.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            callback: Function(symbol, price, data) to call on updates
        """
        if symbol not in self.callbacks:
            self.callbacks[symbol] = []
        self.callbacks[symbol].append(callback)

    def unregister_callback(self, symbol: str, callback: Callable) -> None:
        """Unregister a callback."""
        if symbol in self.callbacks:
            self.callbacks[symbol] = [c for c in self.callbacks[symbol] if c != callback]

    def get_price(self, symbol: str) -> Optional[float]:
        """Get last known price for a symbol."""
        return self.prices.get(symbol)

    def get_all_prices(self) -> Dict[str, float]:
        """Get all last known prices."""
        return self.prices.copy()

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Disconnected from Binance WebSocket")


class PriceFeed:
    """Unified price feed manager for multiple data sources."""

    def __init__(self):
        self.binance_ws: Optional[BinanceWebSocket] = None
        self.prices: Dict[str, Dict] = {}  # symbol -> {price, timestamp, source}
        self.callbacks: List[Callable] = []

    async def start_crypto_feed(self, symbols: List[str]) -> None:
        """Start real-time crypto price feed."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets not available, crypto feed disabled")
            return

        self.binance_ws = BinanceWebSocket()

        # Register price update handler
        for symbol in symbols:
            self.binance_ws.register_callback(symbol, self._on_price_update)

        # Start connection in background
        asyncio.create_task(self.binance_ws.connect(symbols))

    def _on_price_update(self, symbol: str, price: float, data: dict) -> None:
        """Handle price update from any source."""
        self.prices[symbol] = {
            "price": price,
            "timestamp": datetime.now(),
            "source": "binance",
            "change_pct": float(data.get("P", 0)),  # 24h change %
            "volume": float(data.get("v", 0)),  # 24h volume
        }

        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(symbol, self.prices[symbol])
            except Exception as e:
                logger.error(f"Price callback error: {e}")

    def register_callback(self, callback: Callable) -> None:
        """Register callback for all price updates."""
        self.callbacks.append(callback)

    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get price info for a symbol."""
        return self.prices.get(symbol)

    async def stop(self) -> None:
        """Stop all price feeds."""
        if self.binance_ws:
            await self.binance_ws.disconnect()
