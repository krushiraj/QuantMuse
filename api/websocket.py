"""WebSocket handler for real-time updates."""
from typing import Dict, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        # Map of session_id -> set of connected websockets
        self.connections: Dict[int, Set[WebSocket]] = {}
        # All connected websockets (for global broadcasts)
        self.all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.all_connections.add(websocket)

    def subscribe(self, websocket: WebSocket, session_id: int):
        """Subscribe a connection to a session's updates."""
        if session_id not in self.connections:
            self.connections[session_id] = set()
        self.connections[session_id].add(websocket)

    def unsubscribe(self, websocket: WebSocket, session_id: int):
        """Unsubscribe a connection from a session."""
        if session_id in self.connections:
            self.connections[session_id].discard(websocket)

    def disconnect(self, websocket: WebSocket):
        """Handle disconnection."""
        self.all_connections.discard(websocket)
        # Remove from all session subscriptions
        for session_connections in self.connections.values():
            session_connections.discard(websocket)

    async def broadcast(self, message: dict, session_id: int = None):
        """Broadcast message to subscribers."""
        msg_data = {
            **message,
            "timestamp": datetime.now().isoformat()
        }

        if session_id and session_id in self.connections:
            # Broadcast to session subscribers only
            dead_connections = set()
            for connection in self.connections[session_id]:
                try:
                    await connection.send_json(msg_data)
                except Exception:
                    dead_connections.add(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn)
        else:
            # Broadcast to all
            dead_connections = set()
            for connection in self.all_connections:
                try:
                    await connection.send_json(msg_data)
                except Exception:
                    dead_connections.add(connection)

            for conn in dead_connections:
                self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        try:
            await websocket.send_json({
                **message,
                "timestamp": datetime.now().isoformat()
            })
        except Exception:
            self.disconnect(websocket)


# Global manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler."""
    await manager.connect(websocket)

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()

            msg_type = data.get("type")

            if msg_type == "subscribe":
                session_id = data.get("session_id")
                if session_id:
                    manager.subscribe(websocket, session_id)
                    await manager.send_personal(websocket, {
                        "type": "subscribed",
                        "session_id": session_id
                    })

            elif msg_type == "unsubscribe":
                session_id = data.get("session_id")
                if session_id:
                    manager.unsubscribe(websocket, session_id)
                    await manager.send_personal(websocket, {
                        "type": "unsubscribed",
                        "session_id": session_id
                    })

            elif msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Helper functions for broadcasting events
async def broadcast_price_update(session_id: int, symbol: str, price: float, change_pct: float):
    """Broadcast a price update."""
    await manager.broadcast({
        "type": "price_update",
        "data": {
            "symbol": symbol,
            "price": price,
            "change_pct": change_pct
        }
    }, session_id)


async def broadcast_position_update(session_id: int, position_data: dict):
    """Broadcast a position update."""
    await manager.broadcast({
        "type": "position_update",
        "data": position_data
    }, session_id)


async def broadcast_trade_executed(session_id: int, trade_data: dict):
    """Broadcast a trade execution."""
    await manager.broadcast({
        "type": "trade_executed",
        "data": trade_data
    }, session_id)


async def broadcast_signal_generated(session_id: int, signal_data: dict):
    """Broadcast a new signal."""
    await manager.broadcast({
        "type": "signal_generated",
        "data": signal_data
    }, session_id)
