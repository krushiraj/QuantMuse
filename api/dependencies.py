"""FastAPI dependencies for database sessions."""
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
