# Paper Trading Phase 2: API Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete REST API + WebSocket layer for the paper trading dashboard to consume.

**Architecture:** FastAPI application with routers for sessions, positions, trades, signals, performance, and markets. WebSocket for real-time updates. Pydantic schemas for validation.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy (existing models), WebSockets

**Branch:** `feature/paper-trading` (continue from Phase 1)

---

## Task 1: Package Structure & FastAPI App Setup

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/dependencies.py`
- Test: `tests/api/test_main.py`

**Step 1: Write the failing test**

```python
# tests/api/test_main.py
import pytest
from fastapi.testclient import TestClient


def test_app_health_check():
    """Test that the API health endpoint returns OK."""
    from api.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_app_has_cors_enabled():
    """Test that CORS is configured."""
    from api.main import app
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    assert "access-control-allow-origin" in response.headers
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_main.py -v`
Expected: FAIL with "No module named 'api'"

**Step 3: Write minimal implementation**

```python
# api/__init__.py
"""Paper Trading API package."""

# api/dependencies.py
"""FastAPI dependencies for database sessions and common utilities."""
from typing import Generator
from sqlalchemy.orm import Session
from paper_trading.models import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield database session for request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# api/main.py
"""FastAPI application for paper trading dashboard."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Paper Trading API",
    description="API for paper trading dashboard",
    version="1.0.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_main.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/ tests/api/
git commit -m "feat(api): add FastAPI app setup with health check and CORS"
```

---

## Task 2: Pydantic Schemas

**Files:**
- Create: `api/schemas.py`
- Test: `tests/api/test_schemas.py`

**Step 1: Write the failing test**

```python
# tests/api/test_schemas.py
import pytest
from datetime import datetime
from pydantic import ValidationError


def test_session_create_schema():
    """Test SessionCreate schema validation."""
    from api.schemas import SessionCreate

    # Valid input
    data = SessionCreate(name="Test Session", initial_balance=100000)
    assert data.name == "Test Session"
    assert data.initial_balance == 100000

    # Invalid - negative balance
    with pytest.raises(ValidationError):
        SessionCreate(name="Test", initial_balance=-1000)


def test_session_response_schema():
    """Test SessionResponse schema."""
    from api.schemas import SessionResponse

    data = SessionResponse(
        id=1,
        name="Test Session",
        initial_balance=100000,
        current_balance=105000,
        status="active",
        created_at=datetime.now(),
    )
    assert data.id == 1
    assert data.status == "active"


def test_position_response_schema():
    """Test PositionResponse schema with computed fields."""
    from api.schemas import PositionResponse

    data = PositionResponse(
        id=1,
        session_id=1,
        symbol="RELIANCE.NS",
        market="nse",
        direction="long",
        quantity=100,
        entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2375.0,
        take_profit=2875.0,
        trailing_stop=None,
        status="open",
        opened_at=datetime.now(),
        unrealized_pnl=10000.0,
        unrealized_pnl_pct=4.0,
    )
    assert data.symbol == "RELIANCE.NS"
    assert data.unrealized_pnl == 10000.0


def test_trade_response_schema():
    """Test TradeResponse schema."""
    from api.schemas import TradeResponse

    data = TradeResponse(
        id=1,
        session_id=1,
        position_id=1,
        symbol="RELIANCE.NS",
        trade_type="buy",
        quantity=100,
        price=2500.0,
        value=250000.0,
        commission=50.0,
        timestamp=datetime.now(),
    )
    assert data.trade_type == "buy"
    assert data.value == 250000.0


def test_signal_response_schema():
    """Test SignalResponse schema."""
    from api.schemas import SignalResponse

    data = SignalResponse(
        id=1,
        session_id=1,
        symbol="TCS.NS",
        market="nse",
        signal_type="BUY",
        entry_price=3500.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        confidence=0.85,
        strategy="MomentumStrategy",
        status="pending",
        created_at=datetime.now(),
    )
    assert data.signal_type == "BUY"
    assert data.confidence == 0.85


def test_performance_metrics_schema():
    """Test PerformanceMetrics schema."""
    from api.schemas import PerformanceMetrics

    data = PerformanceMetrics(
        total_return_pct=12.5,
        win_rate=65.0,
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        avg_win_pct=8.5,
        avg_loss_pct=-3.2,
        profit_factor=2.1,
        max_drawdown_pct=5.5,
        sharpe_ratio=1.8,
    )
    assert data.win_rate == 65.0
    assert data.profit_factor == 2.1
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_schemas.py -v`
Expected: FAIL with "No module named 'api.schemas'"

**Step 3: Write minimal implementation**

```python
# api/schemas.py
"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# === Session Schemas ===

class SessionCreate(BaseModel):
    """Schema for creating a new trading session."""
    name: str = Field(..., min_length=1, max_length=100)
    initial_balance: float = Field(..., gt=0)

    @field_validator('initial_balance')
    @classmethod
    def validate_balance(cls, v):
        if v <= 0:
            raise ValueError('Initial balance must be positive')
        return v


class SessionResponse(BaseModel):
    """Schema for session response."""
    id: int
    name: str
    initial_balance: float
    current_balance: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    """Schema for session summary with portfolio stats."""
    id: int
    name: str
    initial_balance: float
    current_balance: float
    portfolio_value: float
    cash_balance: float
    invested_value: float
    total_pnl: float
    total_pnl_pct: float
    open_positions: int
    total_trades: int
    status: str


# === Position Schemas ===

class PositionResponse(BaseModel):
    """Schema for position response."""
    id: int
    session_id: int
    symbol: str
    market: str
    direction: str
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float]
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    unrealized_pnl: float
    unrealized_pnl_pct: float

    model_config = {"from_attributes": True}


class PositionClose(BaseModel):
    """Schema for closing a position."""
    reason: str = Field(default="manual", max_length=50)
    close_price: Optional[float] = None


# === Trade Schemas ===

class TradeResponse(BaseModel):
    """Schema for trade response."""
    id: int
    session_id: int
    position_id: Optional[int]
    symbol: str
    trade_type: str
    quantity: int
    price: float
    value: float
    commission: float
    pnl: Optional[float] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class TradeStats(BaseModel):
    """Schema for trade statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float


# === Signal Schemas ===

class SignalCreate(BaseModel):
    """Schema for creating a signal (for testing/manual entry)."""
    symbol: str
    market: str = Field(..., pattern="^(nse|crypto)$")
    signal_type: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    strategy: str


class SignalResponse(BaseModel):
    """Schema for signal response."""
    id: int
    session_id: int
    symbol: str
    market: str
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    factors_json: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SignalAction(BaseModel):
    """Schema for approving/rejecting a signal."""
    action: str = Field(..., pattern="^(approve|reject)$")


# === Performance Schemas ===

class DailyPerformanceResponse(BaseModel):
    """Schema for daily performance snapshot."""
    id: int
    session_id: int
    date: datetime
    portfolio_value: float
    cash_balance: float
    invested_value: float
    daily_pnl: float
    daily_return_pct: float
    cumulative_return_pct: float
    drawdown_pct: float
    num_positions: int
    num_trades: int

    model_config = {"from_attributes": True}


class PerformanceMetrics(BaseModel):
    """Schema for overall performance metrics."""
    total_return_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None


# === Market Schemas ===

class MarketPrice(BaseModel):
    """Schema for market price data."""
    symbol: str
    price: float
    change_pct: float
    volume: Optional[float] = None
    timestamp: datetime


class MarketStatus(BaseModel):
    """Schema for market status."""
    market: str
    is_open: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None


# === WebSocket Schemas ===

class WSMessage(BaseModel):
    """Schema for WebSocket messages."""
    type: str  # price_update, position_update, trade_executed, signal_generated
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/schemas.py tests/api/test_schemas.py
git commit -m "feat(api): add Pydantic schemas for all API endpoints"
```

---

## Task 3: Sessions Router

**Files:**
- Create: `api/routers/__init__.py`
- Create: `api/routers/sessions.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_sessions.py`

**Step 1: Write the failing test**

```python
# tests/api/test_sessions.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_session(client):
    """Test creating a new trading session."""
    response = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Session"
    assert data["initial_balance"] == 100000
    assert data["status"] == "active"
    assert "id" in data


def test_list_sessions(client):
    """Test listing all sessions."""
    # Create two sessions
    client.post("/api/sessions", json={"name": "Session 1", "initial_balance": 100000})
    client.post("/api/sessions", json={"name": "Session 2", "initial_balance": 200000})

    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_session(client):
    """Test getting a specific session."""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    session_id = create_resp.json()["id"]

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Session"


def test_get_session_not_found(client):
    """Test getting non-existent session returns 404."""
    response = client.get("/api/sessions/999")
    assert response.status_code == 404


def test_get_session_summary(client):
    """Test getting session summary with portfolio stats."""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    session_id = create_resp.json()["id"]

    response = client.get(f"/api/sessions/{session_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert "portfolio_value" in data
    assert "open_positions" in data
    assert "total_pnl" in data
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_sessions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/__init__.py
"""API routers package."""

# api/routers/sessions.py
"""Sessions router for managing trading sessions."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SessionCreate, SessionResponse, SessionSummary
from paper_trading.models import PaperSession, PaperPosition, PaperTrade

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    """Create a new trading session."""
    session = PaperSession(
        name=session_data.name,
        initial_balance=session_data.initial_balance,
        current_balance=session_data.initial_balance,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all trading sessions."""
    query = db.query(PaperSession)
    if status:
        query = query.filter(PaperSession.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific session by ID."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/summary", response_model=SessionSummary)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    """Get session summary with portfolio statistics."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get open positions
    open_positions = db.query(PaperPosition).filter(
        PaperPosition.session_id == session_id,
        PaperPosition.status == "open"
    ).all()

    # Calculate invested value
    invested_value = sum(p.quantity * p.entry_price for p in open_positions)

    # Calculate unrealized P&L
    unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)

    # Get total trades
    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    # Calculate portfolio value
    portfolio_value = session.current_balance + invested_value + unrealized_pnl

    # Calculate total P&L
    total_pnl = portfolio_value - session.initial_balance
    total_pnl_pct = (total_pnl / session.initial_balance) * 100 if session.initial_balance > 0 else 0

    return SessionSummary(
        id=session.id,
        name=session.name,
        initial_balance=session.initial_balance,
        current_balance=session.current_balance,
        portfolio_value=portfolio_value,
        cash_balance=session.current_balance,
        invested_value=invested_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        open_positions=len(open_positions),
        total_trades=total_trades,
        status=session.status,
    )


@router.patch("/{session_id}/end")
def end_session(session_id: int, db: Session = Depends(get_db)):
    """End a trading session."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ended"
    db.commit()
    return {"message": "Session ended", "session_id": session_id}
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py - add after existing code
from api.routers import sessions

app.include_router(sessions.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_sessions.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/ api/main.py tests/api/test_sessions.py
git commit -m "feat(api): add sessions router with CRUD operations"
```

---

## Task 4: Positions Router

**Files:**
- Create: `api/routers/positions.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_positions.py`

**Step 1: Write the failing test**

```python
# tests/api/test_positions.py
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base, PaperSession, PaperPosition


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(test_db):
    """Set up test session and positions."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=90000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create positions
    pos1 = PaperPosition(
        session_id=session.id,
        symbol="RELIANCE.NS",
        market="nse",
        direction="long",
        quantity=100,
        entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2375.0,
        take_profit=2875.0,
        status="open",
    )
    pos2 = PaperPosition(
        session_id=session.id,
        symbol="TCS.NS",
        market="nse",
        direction="long",
        quantity=50,
        entry_price=3500.0,
        current_price=3400.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        status="open",
    )
    db.add_all([pos1, pos2])
    db.commit()

    db.close()
    return session.id


def test_list_positions(client, setup_data):
    """Test listing open positions."""
    session_id = setup_data
    response = client.get(f"/api/positions?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_positions_filter_by_status(client, setup_data):
    """Test filtering positions by status."""
    session_id = setup_data
    response = client.get(f"/api/positions?session_id={session_id}&status=open")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(p["status"] == "open" for p in data)


def test_get_position(client, setup_data):
    """Test getting a specific position."""
    session_id = setup_data
    # First get list to get position ID
    list_resp = client.get(f"/api/positions?session_id={session_id}")
    position_id = list_resp.json()[0]["id"]

    response = client.get(f"/api/positions/{position_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE.NS"
    assert "unrealized_pnl" in data


def test_close_position(client, setup_data):
    """Test closing a position manually."""
    session_id = setup_data
    list_resp = client.get(f"/api/positions?session_id={session_id}")
    position_id = list_resp.json()[0]["id"]

    response = client.post(
        f"/api/positions/{position_id}/close",
        json={"reason": "manual", "close_price": 2650.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["close_reason"] == "manual"
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_positions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/positions.py
"""Positions router for managing trading positions."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import PositionResponse, PositionClose
from paper_trading.models import PaperPosition, PaperSession, PaperTrade

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=List[PositionResponse])
def list_positions(
    session_id: int = Query(..., description="Session ID to filter positions"),
    status: Optional[str] = Query(None, description="Filter by status (open/closed)"),
    market: Optional[str] = Query(None, description="Filter by market (nse/crypto)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List positions for a session."""
    query = db.query(PaperPosition).filter(PaperPosition.session_id == session_id)

    if status:
        query = query.filter(PaperPosition.status == status)
    if market:
        query = query.filter(PaperPosition.market == market)

    positions = query.offset(skip).limit(limit).all()

    # Add computed fields
    result = []
    for pos in positions:
        pos_dict = {
            "id": pos.id,
            "session_id": pos.session_id,
            "symbol": pos.symbol,
            "market": pos.market,
            "direction": pos.direction,
            "quantity": pos.quantity,
            "entry_price": pos.entry_price,
            "current_price": pos.current_price,
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
            "trailing_stop": pos.trailing_stop,
            "status": pos.status,
            "opened_at": pos.opened_at,
            "closed_at": pos.closed_at,
            "close_reason": pos.close_reason,
            "unrealized_pnl": pos.unrealized_pnl,
            "unrealized_pnl_pct": (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100 if pos.entry_price and pos.quantity else 0,
        }
        result.append(pos_dict)

    return result


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db)):
    """Get a specific position by ID."""
    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    return {
        "id": position.id,
        "session_id": position.session_id,
        "symbol": position.symbol,
        "market": position.market,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "trailing_stop": position.trailing_stop,
        "status": position.status,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "close_reason": position.close_reason,
        "unrealized_pnl": position.unrealized_pnl,
        "unrealized_pnl_pct": (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price and position.quantity else 0,
    }


@router.post("/{position_id}/close", response_model=PositionResponse)
def close_position(
    position_id: int,
    close_data: PositionClose,
    db: Session = Depends(get_db)
):
    """Manually close a position."""
    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.status == "closed":
        raise HTTPException(status_code=400, detail="Position already closed")

    # Determine close price
    close_price = close_data.close_price or position.current_price

    # Calculate P&L
    if position.direction == "long":
        pnl = (close_price - position.entry_price) * position.quantity
    else:
        pnl = (position.entry_price - close_price) * position.quantity

    # Update position
    position.status = "closed"
    position.close_reason = close_data.reason
    position.closed_at = datetime.now()
    position.current_price = close_price

    # Update session balance
    session = db.query(PaperSession).filter(PaperSession.id == position.session_id).first()
    if session:
        # Return capital + P&L
        session.current_balance += (position.entry_price * position.quantity) + pnl

    # Create sell trade record
    trade = PaperTrade(
        session_id=position.session_id,
        position_id=position.id,
        symbol=position.symbol,
        trade_type="sell",
        quantity=position.quantity,
        price=close_price,
        value=close_price * position.quantity,
        commission=0,  # TODO: Calculate commission
        pnl=pnl,
    )
    db.add(trade)

    db.commit()
    db.refresh(position)

    return {
        "id": position.id,
        "session_id": position.session_id,
        "symbol": position.symbol,
        "market": position.market,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "trailing_stop": position.trailing_stop,
        "status": position.status,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "close_reason": position.close_reason,
        "unrealized_pnl": 0,  # Closed position has no unrealized P&L
        "unrealized_pnl_pct": 0,
    }


@router.get("/{position_id}/history")
def get_position_history(position_id: int, db: Session = Depends(get_db)):
    """Get adjustment history for a position."""
    from paper_trading.models import PositionAdjustment

    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    adjustments = db.query(PositionAdjustment).filter(
        PositionAdjustment.position_id == position_id
    ).order_by(PositionAdjustment.timestamp.desc()).all()

    return [
        {
            "id": adj.id,
            "adjustment_type": adj.adjustment_type,
            "old_stop_loss": adj.old_stop_loss,
            "new_stop_loss": adj.new_stop_loss,
            "old_take_profit": adj.old_take_profit,
            "new_take_profit": adj.new_take_profit,
            "reason": adj.reason,
            "timestamp": adj.timestamp,
        }
        for adj in adjustments
    ]
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py
from api.routers import sessions, positions

app.include_router(sessions.router)
app.include_router(positions.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_positions.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/positions.py api/main.py tests/api/test_positions.py
git commit -m "feat(api): add positions router with list, get, close, and history"
```

---

## Task 5: Trades Router

**Files:**
- Create: `api/routers/trades.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_trades.py`

**Step 1: Write the failing test**

```python
# tests/api/test_trades.py
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base, PaperSession, PaperTrade


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(test_db):
    """Set up test session and trades."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=95000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create trades
    trades = [
        PaperTrade(session_id=session.id, position_id=1, symbol="RELIANCE.NS",
                   trade_type="buy", quantity=100, price=2500, value=250000, commission=50, pnl=None),
        PaperTrade(session_id=session.id, position_id=1, symbol="RELIANCE.NS",
                   trade_type="sell", quantity=100, price=2650, value=265000, commission=50, pnl=14900),
        PaperTrade(session_id=session.id, position_id=2, symbol="TCS.NS",
                   trade_type="buy", quantity=50, price=3500, value=175000, commission=35, pnl=None),
        PaperTrade(session_id=session.id, position_id=2, symbol="TCS.NS",
                   trade_type="sell", quantity=50, price=3400, value=170000, commission=35, pnl=-5070),
    ]
    db.add_all(trades)
    db.commit()

    db.close()
    return session.id


def test_list_trades(client, setup_data):
    """Test listing trades."""
    session_id = setup_data
    response = client.get(f"/api/trades?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4


def test_list_trades_filter_by_type(client, setup_data):
    """Test filtering trades by type."""
    session_id = setup_data
    response = client.get(f"/api/trades?session_id={session_id}&trade_type=sell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(t["trade_type"] == "sell" for t in data)


def test_get_trade_stats(client, setup_data):
    """Test getting trade statistics."""
    session_id = setup_data
    response = client.get(f"/api/trades/stats?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_trades"] == 4
    assert data["winning_trades"] == 1
    assert data["losing_trades"] == 1
    assert "win_rate" in data
    assert "total_pnl" in data
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_trades.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/trades.py
"""Trades router for trade history and statistics."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencies import get_db
from api.schemas import TradeResponse, TradeStats
from paper_trading.models import PaperTrade

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=List[TradeResponse])
def list_trades(
    session_id: int = Query(..., description="Session ID"),
    trade_type: Optional[str] = Query(None, description="Filter by type (buy/sell)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List trades for a session."""
    query = db.query(PaperTrade).filter(PaperTrade.session_id == session_id)

    if trade_type:
        query = query.filter(PaperTrade.trade_type == trade_type)
    if symbol:
        query = query.filter(PaperTrade.symbol == symbol)

    trades = query.order_by(PaperTrade.timestamp.desc()).offset(skip).limit(limit).all()
    return trades


@router.get("/stats", response_model=TradeStats)
def get_trade_stats(
    session_id: int = Query(..., description="Session ID"),
    db: Session = Depends(get_db)
):
    """Get trade statistics for a session."""
    # Get all sell trades (which have P&L)
    sell_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id,
        PaperTrade.trade_type == "sell"
    ).all()

    # Count all trades
    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    # Calculate stats
    winning_trades = [t for t in sell_trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in sell_trades if t.pnl and t.pnl < 0]

    total_pnl = sum(t.pnl or 0 for t in sell_trades)

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    completed_trades = win_count + loss_count

    win_rate = (win_count / completed_trades * 100) if completed_trades > 0 else 0

    avg_win = sum(t.pnl for t in winning_trades) / win_count if win_count > 0 else 0
    avg_loss = sum(t.pnl for t in losing_trades) / loss_count if loss_count > 0 else 0

    largest_win = max((t.pnl for t in winning_trades), default=0)
    largest_loss = min((t.pnl for t in losing_trades), default=0)

    return TradeStats(
        total_trades=total_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
    )
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py
from api.routers import sessions, positions, trades

app.include_router(sessions.router)
app.include_router(positions.router)
app.include_router(trades.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_trades.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/trades.py api/main.py tests/api/test_trades.py
git commit -m "feat(api): add trades router with list and statistics"
```

---

## Task 6: Signals Router

**Files:**
- Create: `api/routers/signals.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_signals.py`

**Step 1: Write the failing test**

```python
# tests/api/test_signals.py
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base, PaperSession, PendingSignal


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(test_db):
    """Set up test session and signals."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=100000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create signals
    signals = [
        PendingSignal(
            session_id=session.id, symbol="RELIANCE.NS", market="nse",
            signal_type="BUY", entry_price=2500, stop_loss=2375, take_profit=2875,
            confidence=0.85, strategy="MomentumStrategy", status="pending"
        ),
        PendingSignal(
            session_id=session.id, symbol="TCS.NS", market="nse",
            signal_type="BUY", entry_price=3500, stop_loss=3325, take_profit=4025,
            confidence=0.72, strategy="MultiFactorStrategy", status="pending"
        ),
    ]
    db.add_all(signals)
    db.commit()

    db.close()
    return session.id


def test_list_signals(client, setup_data):
    """Test listing pending signals."""
    session_id = setup_data
    response = client.get(f"/api/signals?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_signals_filter_by_status(client, setup_data):
    """Test filtering signals by status."""
    session_id = setup_data
    response = client.get(f"/api/signals?session_id={session_id}&status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_approve_signal(client, setup_data):
    """Test approving a signal."""
    session_id = setup_data
    list_resp = client.get(f"/api/signals?session_id={session_id}")
    signal_id = list_resp.json()[0]["id"]

    response = client.post(
        f"/api/signals/{signal_id}/action",
        json={"action": "approve"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"


def test_reject_signal(client, setup_data):
    """Test rejecting a signal."""
    session_id = setup_data
    list_resp = client.get(f"/api/signals?session_id={session_id}")
    signal_id = list_resp.json()[1]["id"]

    response = client.post(
        f"/api/signals/{signal_id}/action",
        json={"action": "reject"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_signals.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/signals.py
"""Signals router for managing pending trading signals."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SignalResponse, SignalAction, SignalCreate
from paper_trading.models import PendingSignal, PaperSession

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=List[SignalResponse])
def list_signals(
    session_id: int = Query(..., description="Session ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending/executed/rejected)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List signals for a session."""
    query = db.query(PendingSignal).filter(PendingSignal.session_id == session_id)

    if status:
        query = query.filter(PendingSignal.status == status)

    signals = query.order_by(PendingSignal.created_at.desc()).offset(skip).limit(limit).all()
    return signals


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a specific signal."""
    signal = db.query(PendingSignal).filter(PendingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("", response_model=SignalResponse, status_code=201)
def create_signal(
    session_id: int,
    signal_data: SignalCreate,
    db: Session = Depends(get_db)
):
    """Create a new signal (for testing/manual entry)."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    signal = PendingSignal(
        session_id=session_id,
        symbol=signal_data.symbol,
        market=signal_data.market,
        signal_type=signal_data.signal_type,
        entry_price=signal_data.entry_price,
        stop_loss=signal_data.stop_loss,
        take_profit=signal_data.take_profit,
        confidence=signal_data.confidence,
        strategy=signal_data.strategy,
        status="pending",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.post("/{signal_id}/action", response_model=SignalResponse)
def signal_action(
    signal_id: int,
    action_data: SignalAction,
    db: Session = Depends(get_db)
):
    """Approve or reject a signal."""
    signal = db.query(PendingSignal).filter(PendingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    if signal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Signal already {signal.status}")

    if action_data.action == "approve":
        signal.status = "executed"
        signal.reviewed_at = datetime.now()
        # TODO: Create position via paper executor
        # For now, just mark as executed
    elif action_data.action == "reject":
        signal.status = "rejected"
        signal.reviewed_at = datetime.now()

    db.commit()
    db.refresh(signal)
    return signal
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py
from api.routers import sessions, positions, trades, signals

app.include_router(sessions.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(signals.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_signals.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/signals.py api/main.py tests/api/test_signals.py
git commit -m "feat(api): add signals router with list, create, and approve/reject"
```

---

## Task 7: Performance Router

**Files:**
- Create: `api/routers/performance.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_performance.py`

**Step 1: Write the failing test**

```python
# tests/api/test_performance.py
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base, PaperSession, DailyPerformance, PaperTrade


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(test_db):
    """Set up test session with performance data."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=112000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create daily performance snapshots
    today = datetime.now().date()
    for i in range(5):
        perf = DailyPerformance(
            session_id=session.id,
            date=today - timedelta(days=4-i),
            portfolio_value=100000 + (i * 3000),
            cash_balance=50000,
            invested_value=50000 + (i * 3000),
            daily_pnl=3000 if i > 0 else 0,
            daily_return_pct=3.0 if i > 0 else 0,
            cumulative_return_pct=i * 3.0,
            drawdown_pct=0,
            num_positions=2,
            num_trades=i * 2,
        )
        db.add(perf)

    # Create trades for metrics
    trades = [
        PaperTrade(session_id=session.id, position_id=1, symbol="A",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=500),
        PaperTrade(session_id=session.id, position_id=2, symbol="B",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=800),
        PaperTrade(session_id=session.id, position_id=3, symbol="C",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=-200),
    ]
    db.add_all(trades)
    db.commit()

    db.close()
    return session.id


def test_get_daily_performance(client, setup_data):
    """Test getting daily performance data."""
    session_id = setup_data
    response = client.get(f"/api/performance/daily?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_get_performance_metrics(client, setup_data):
    """Test getting performance metrics."""
    session_id = setup_data
    response = client.get(f"/api/performance/metrics?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert "total_return_pct" in data
    assert "win_rate" in data
    assert "max_drawdown_pct" in data
    assert data["winning_trades"] == 2
    assert data["losing_trades"] == 1
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_performance.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/performance.py
"""Performance router for analytics and metrics."""
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import DailyPerformanceResponse, PerformanceMetrics
from paper_trading.models import DailyPerformance, PaperSession, PaperTrade

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/daily", response_model=List[DailyPerformanceResponse])
def get_daily_performance(
    session_id: int = Query(..., description="Session ID"),
    days: int = Query(30, description="Number of days to return"),
    db: Session = Depends(get_db)
):
    """Get daily performance snapshots."""
    cutoff_date = datetime.now() - timedelta(days=days)

    snapshots = db.query(DailyPerformance).filter(
        DailyPerformance.session_id == session_id,
        DailyPerformance.date >= cutoff_date
    ).order_by(DailyPerformance.date.asc()).all()

    return snapshots


@router.get("/metrics", response_model=PerformanceMetrics)
def get_performance_metrics(
    session_id: int = Query(..., description="Session ID"),
    db: Session = Depends(get_db)
):
    """Calculate overall performance metrics."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        return PerformanceMetrics(
            total_return_pct=0, win_rate=0, total_trades=0,
            winning_trades=0, losing_trades=0, avg_win_pct=0,
            avg_loss_pct=0, profit_factor=0, max_drawdown_pct=0
        )

    # Get all completed trades (sells with P&L)
    sell_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id,
        PaperTrade.trade_type == "sell",
        PaperTrade.pnl.isnot(None)
    ).all()

    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    winning = [t for t in sell_trades if t.pnl > 0]
    losing = [t for t in sell_trades if t.pnl < 0]

    win_count = len(winning)
    loss_count = len(losing)
    completed = win_count + loss_count

    # Calculate metrics
    total_return_pct = ((session.current_balance - session.initial_balance)
                        / session.initial_balance * 100) if session.initial_balance > 0 else 0

    win_rate = (win_count / completed * 100) if completed > 0 else 0

    total_wins = sum(t.pnl for t in winning)
    total_losses = abs(sum(t.pnl for t in losing))

    avg_win = total_wins / win_count if win_count > 0 else 0
    avg_loss = total_losses / loss_count if loss_count > 0 else 0

    # Approximate percentages
    avg_win_pct = (avg_win / session.initial_balance * 100) if session.initial_balance > 0 else 0
    avg_loss_pct = (-avg_loss / session.initial_balance * 100) if session.initial_balance > 0 else 0

    profit_factor = (total_wins / total_losses) if total_losses > 0 else (float('inf') if total_wins > 0 else 0)

    # Get max drawdown from daily snapshots
    snapshots = db.query(DailyPerformance).filter(
        DailyPerformance.session_id == session_id
    ).all()
    max_drawdown = max((s.drawdown_pct for s in snapshots), default=0)

    return PerformanceMetrics(
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        profit_factor=profit_factor if profit_factor != float('inf') else 999.99,
        max_drawdown_pct=max_drawdown,
    )
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py
from api.routers import sessions, positions, trades, signals, performance

app.include_router(sessions.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(signals.router)
app.include_router(performance.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_performance.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/performance.py api/main.py tests/api/test_performance.py
git commit -m "feat(api): add performance router with daily snapshots and metrics"
```

---

## Task 8: Markets Router

**Files:**
- Create: `api/routers/markets.py`
- Update: `api/main.py` (include router)
- Test: `tests/api/test_markets.py`

**Step 1: Write the failing test**

```python
# tests/api/test_markets.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_market_status(client):
    """Test getting market status."""
    response = client.get("/api/markets/status")
    assert response.status_code == 200
    data = response.json()
    assert "nse" in data
    assert "crypto" in data
    assert "is_open" in data["nse"]


@patch('api.routers.markets.NSEFetcher')
def test_get_prices(mock_fetcher_class, client):
    """Test getting prices for watchlist."""
    mock_fetcher = MagicMock()
    mock_fetcher.get_current_price.return_value = 2500.0
    mock_fetcher_class.return_value = mock_fetcher

    response = client.get("/api/markets/prices?symbols=RELIANCE.NS,TCS.NS")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_watchlist(client):
    """Test getting default watchlist."""
    response = client.get("/api/markets/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert "nse" in data
    assert "crypto" in data
    assert len(data["nse"]) > 0
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_markets.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/routers/markets.py
"""Markets router for market data and prices."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Query

from api.schemas import MarketPrice, MarketStatus
from paper_trading.config import PaperTradingConfig

router = APIRouter(prefix="/api/markets", tags=["markets"])

# Default watchlists from config
DEFAULT_NSE_WATCHLIST = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS",
    "ICICIBANK.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "ITC.NS", "SBIN.NS"
]

DEFAULT_CRYPTO_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"
]


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
            price = nse_fetcher.get_current_price(symbol)
            # TODO: Calculate change_pct from previous close
            prices.append(MarketPrice(
                symbol=symbol,
                price=price,
                change_pct=0.0,  # Placeholder
                timestamp=datetime.now()
            ))
        except Exception:
            # Skip symbols that fail
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

    nse_fetcher = NSEFetcher()

    try:
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
```

**Step 4: Update main.py to include router**

```python
# Update api/main.py
from api.routers import sessions, positions, trades, signals, performance, markets

app.include_router(sessions.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(signals.router)
app.include_router(performance.router)
app.include_router(markets.router)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_markets.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/routers/markets.py api/main.py tests/api/test_markets.py
git commit -m "feat(api): add markets router with status, prices, and watchlist"
```

---

## Task 9: WebSocket Handler

**Files:**
- Create: `api/websocket.py`
- Update: `api/main.py` (add WebSocket endpoint)
- Test: `tests/api/test_websocket.py`

**Step 1: Write the failing test**

```python
# tests/api/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from paper_trading.models import Base


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_websocket_connect(client):
    """Test WebSocket connection."""
    with client.websocket_connect("/api/ws") as websocket:
        # Send subscription message
        websocket.send_json({"type": "subscribe", "session_id": 1})

        # Should receive acknowledgment
        data = websocket.receive_json()
        assert data["type"] == "subscribed"


def test_websocket_manager_broadcast():
    """Test WebSocket manager broadcast function."""
    from api.websocket import ConnectionManager

    manager = ConnectionManager()
    # Just verify manager can be instantiated
    assert manager is not None
    assert hasattr(manager, 'broadcast')
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/api/test_websocket.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# api/websocket.py
"""WebSocket handler for real-time updates."""
from typing import Dict, List, Set
from datetime import datetime
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect

from api.schemas import WSMessage


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
```

**Step 4: Update main.py to add WebSocket endpoint**

```python
# Update api/main.py - add WebSocket import and endpoint
from api.websocket import websocket_endpoint

# Add after router includes
@app.websocket("/api/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket)
```

**Step 5: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/api/test_websocket.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/websocket.py api/main.py tests/api/test_websocket.py
git commit -m "feat(api): add WebSocket handler for real-time updates"
```

---

## Task 10: API Runner Script & Final Integration

**Files:**
- Create: `scripts/run_api_server.py`
- Test: Run full integration test

**Step 1: Create API runner script**

```python
# scripts/run_api_server.py
#!/usr/bin/env python3
"""Run the Paper Trading API server."""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run Paper Trading API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")

    args = parser.parse_args()

    print(f"Starting Paper Trading API on {args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    print(f"WebSocket: ws://{args.host}:{args.port}/api/ws")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
```

**Step 2: Run all API tests**

Run: `source venv/bin/activate && pytest tests/api/ -v`
Expected: All tests pass

**Step 3: Run integration test - start server and test endpoints**

Run: `source venv/bin/activate && python scripts/run_api_server.py &`
Test: `curl http://localhost:8000/health`
Expected: `{"status": "healthy"}`

**Step 4: Commit**

```bash
git add scripts/run_api_server.py
git commit -m "feat(api): add API server runner script"
```

---

## Summary

Phase 2 creates a complete REST API layer with:
- **Sessions**: Create, list, get, summary, end
- **Positions**: List, get, close, history
- **Trades**: List, statistics
- **Signals**: List, create, approve/reject
- **Performance**: Daily snapshots, metrics
- **Markets**: Status, prices, watchlist, quote
- **WebSocket**: Real-time updates for positions, trades, signals

All endpoints are documented at `/docs` (Swagger UI) when the server is running.
