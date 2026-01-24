"""Tests for Binance WebSocket client."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json


def test_binance_websocket_import():
    """Test BinanceWebSocket can be imported."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    assert BinanceWebSocket is not None


def test_price_feed_import():
    """Test PriceFeed can be imported."""
    from data_service.fetchers.binance_websocket import PriceFeed
    assert PriceFeed is not None


def test_get_stream_name():
    """Test stream name generation."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    assert ws._get_stream_name("BTCUSDT") == "btcusdt@ticker"
    assert ws._get_stream_name("ETHUSDT", "trade") == "ethusdt@trade"


def test_register_callback():
    """Test callback registration."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    callback = MagicMock()

    ws.register_callback("BTCUSDT", callback)
    assert "BTCUSDT" in ws.callbacks
    assert callback in ws.callbacks["BTCUSDT"]


def test_unregister_callback():
    """Test callback unregistration."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    callback = MagicMock()

    ws.register_callback("BTCUSDT", callback)
    ws.unregister_callback("BTCUSDT", callback)
    assert callback not in ws.callbacks.get("BTCUSDT", [])


def test_price_feed_callback():
    """Test PriceFeed callback registration."""
    from data_service.fetchers.binance_websocket import PriceFeed

    feed = PriceFeed()
    callback = MagicMock()

    feed.register_callback(callback)
    assert callback in feed.callbacks


@pytest.mark.asyncio
async def test_handle_message():
    """Test message handling."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    callback = MagicMock()
    ws.register_callback("BTCUSDT", callback)

    # Simulate ticker message
    message = json.dumps({
        "stream": "btcusdt@ticker",
        "data": {
            "e": "24hrTicker",
            "s": "BTCUSDT",
            "c": "50000.00",
            "P": "2.5",
            "v": "1000000"
        }
    })

    await ws._handle_message(message)

    assert ws.prices["BTCUSDT"] == 50000.0
    callback.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_async_callback():
    """Test message handling with async callback."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    async_callback = AsyncMock()
    ws.register_callback("ETHUSDT", async_callback)

    # Simulate ticker message
    message = json.dumps({
        "stream": "ethusdt@ticker",
        "data": {
            "e": "24hrTicker",
            "s": "ETHUSDT",
            "c": "3000.00",
            "P": "1.5",
            "v": "500000"
        }
    })

    await ws._handle_message(message)

    assert ws.prices["ETHUSDT"] == 3000.0
    async_callback.assert_called_once()


def test_get_price():
    """Test get_price method."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    ws.prices["BTCUSDT"] = 50000.0

    assert ws.get_price("BTCUSDT") == 50000.0
    assert ws.get_price("UNKNOWN") is None


def test_get_all_prices():
    """Test get_all_prices method."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    ws.prices["BTCUSDT"] = 50000.0
    ws.prices["ETHUSDT"] = 3000.0

    all_prices = ws.get_all_prices()
    assert all_prices == {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}
    # Ensure it's a copy
    all_prices["BTCUSDT"] = 0
    assert ws.prices["BTCUSDT"] == 50000.0


def test_price_feed_get_price():
    """Test PriceFeed get_price method."""
    from data_service.fetchers.binance_websocket import PriceFeed
    from datetime import datetime

    feed = PriceFeed()
    feed.prices["BTCUSDT"] = {
        "price": 50000.0,
        "timestamp": datetime.now(),
        "source": "binance",
        "change_pct": 2.5,
        "volume": 1000000.0,
    }

    price_info = feed.get_price("BTCUSDT")
    assert price_info is not None
    assert price_info["price"] == 50000.0
    assert price_info["source"] == "binance"
    assert feed.get_price("UNKNOWN") is None


def test_price_feed_on_price_update():
    """Test PriceFeed _on_price_update method."""
    from data_service.fetchers.binance_websocket import PriceFeed

    feed = PriceFeed()
    callback = MagicMock()
    feed.register_callback(callback)

    # Simulate price update
    data = {"P": "2.5", "v": "1000000"}
    feed._on_price_update("BTCUSDT", 50000.0, data)

    assert "BTCUSDT" in feed.prices
    assert feed.prices["BTCUSDT"]["price"] == 50000.0
    assert feed.prices["BTCUSDT"]["change_pct"] == 2.5
    callback.assert_called_once()


@pytest.mark.asyncio
async def test_handle_invalid_json():
    """Test handling of invalid JSON message."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    # Should not raise exception
    await ws._handle_message("invalid json{")
    assert len(ws.prices) == 0


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnect method."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    ws.running = True
    ws.websocket = AsyncMock()

    await ws.disconnect()

    assert ws.running is False
    assert ws.websocket is None


def test_stream_url_constants():
    """Test WebSocket URL constants."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    assert "stream.binance.com" in ws.STREAM_URL
    assert "stream.binance.com" in ws.STREAM_URL_COMBINED


def test_multiple_callbacks_same_symbol():
    """Test registering multiple callbacks for same symbol."""
    from data_service.fetchers.binance_websocket import BinanceWebSocket, WEBSOCKETS_AVAILABLE
    if not WEBSOCKETS_AVAILABLE:
        pytest.skip("websockets not installed")

    ws = BinanceWebSocket()
    callback1 = MagicMock()
    callback2 = MagicMock()

    ws.register_callback("BTCUSDT", callback1)
    ws.register_callback("BTCUSDT", callback2)

    assert len(ws.callbacks["BTCUSDT"]) == 2
    assert callback1 in ws.callbacks["BTCUSDT"]
    assert callback2 in ws.callbacks["BTCUSDT"]
