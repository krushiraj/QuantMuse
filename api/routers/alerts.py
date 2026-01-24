"""Alerts router for notification management."""
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime

from paper_trading.alerts import alert_manager, AlertType, Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: str
    type: str
    priority: int
    title: str
    message: str
    data: dict
    timestamp: datetime
    session_id: Optional[int]
    read: bool


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    session_id: Optional[int] = Query(None),
    alert_type: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
):
    """Get alerts with optional filters."""
    type_filter = None
    if alert_type:
        try:
            type_filter = AlertType(alert_type)
        except ValueError:
            raise HTTPException(400, f"Invalid alert type: {alert_type}")

    alerts = alert_manager.get_alerts(
        session_id=session_id,
        alert_type=type_filter,
        unread_only=unread_only,
        limit=limit,
    )

    return [
        AlertResponse(
            id=a.id,
            type=a.alert_type.value,
            priority=a.priority.value,
            title=a.title,
            message=a.message,
            data=a.data,
            timestamp=a.timestamp,
            session_id=a.session_id,
            read=a.read,
        )
        for a in alerts
    ]


@router.post("/{alert_id}/read")
def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    if alert_manager.mark_read(alert_id):
        return {"message": "Alert marked as read"}
    raise HTTPException(404, "Alert not found")


@router.post("/read-all")
def mark_all_read(session_id: Optional[int] = Query(None)):
    """Mark all alerts as read."""
    count = alert_manager.mark_all_read(session_id)
    return {"message": f"Marked {count} alerts as read"}


@router.delete("")
def clear_alerts(session_id: Optional[int] = Query(None)):
    """Clear alerts."""
    count = alert_manager.clear_alerts(session_id)
    return {"message": f"Cleared {count} alerts"}
