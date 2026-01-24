#!/usr/bin/env python3
"""Run the Paper Trading API server."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize database before starting server
from paper_trading.models import Base, engine
Base.metadata.create_all(engine)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
