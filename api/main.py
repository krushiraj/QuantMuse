"""FastAPI application for paper trading dashboard."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import sessions, positions, trades, signals

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

# Include routers
app.include_router(sessions.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(signals.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
