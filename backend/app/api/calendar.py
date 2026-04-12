"""
api/calendar.py

Endpoints for Google Calendar integration status.
Actual event creation/deletion is triggered automatically by the
assign, complete, and fail endpoints in api/tasks.py.
"""

from fastapi import APIRouter
from app.services.calendar_service import is_authorized

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/status")
def calendar_status():
    """
    Returns whether Google Calendar is currently authorized.
    The frontend uses this to show a 'Connect Calendar' prompt if not.
    """
    authorized = is_authorized()
    return {
        "authorized": authorized,
        "message": (
            "Google Calendar is connected."
            if authorized
            else "Not authorized. Run: python -m app.services.calendar_auth in your backend directory."
        ),
    }
