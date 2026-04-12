"""
services/calendar_service.py

Handles all communication with the Google Calendar API.

Prerequisites (do these manually before using this service):
  1. Go to https://console.cloud.google.com
  2. Create a project named "TDMS"
  3. Enable the "Google Calendar API"
  4. Go to APIs & Services → Credentials
  5. Create OAuth 2.0 Client ID → Desktop App
  6. Download the JSON file and save it as: backend/google_credentials.json
  7. Add google_credentials.json to .gitignore (already done)

On first use, run the helper script below to authorize:
  cd backend
  python -m app.services.calendar_auth

This creates backend/token.json which stores your access + refresh tokens.
All subsequent calendar calls use token.json automatically.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The scope we need: create/read/update/delete events
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Paths — relative to where the backend is run from (i.e., the backend/ directory)
CREDENTIALS_FILE = "google_credentials.json"
TOKEN_FILE = "token.json"

# Maps urgency level to Google Calendar color ID
# Google's color IDs: 1=Lavender 2=Sage 3=Grape 4=Flamingo 5=Banana
# 6=Tangerine 7=Peacock 8=Graphite 9=Blueberry 10=Basil 11=Tomato
URGENCY_COLOR_MAP = {
    1: "11",  # Very High → Tomato (red)
    2: "6",   # High → Tangerine (orange)
    3: "5",   # Medium → Banana (yellow)
    4: "7",   # Low → Peacock (blue)
    5: "2",   # Very Low → Sage (green)
}


def _get_credentials() -> Optional[Credentials]:
    """
    Loads saved credentials from token.json.
    If the token is expired, automatically refreshes it using the refresh token.
    Returns None if no token file exists (user hasn't authorized yet).
    """
    if not os.path.exists(TOKEN_FILE):
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save the refreshed token back to disk
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"[Calendar] Token refresh failed: {e}")
            return None

    return creds if creds and creds.valid else None


def _build_service():
    """
    Builds and returns an authorized Google Calendar API client.
    Raises RuntimeError if not authorized.
    """
    creds = _get_credentials()
    if not creds:
        raise RuntimeError(
            "Google Calendar is not authorized. "
            "Run: python -m app.services.calendar_auth"
        )
    return build("calendar", "v3", credentials=creds)


def is_authorized() -> bool:
    """Returns True if a valid token exists and is usable."""
    try:
        creds = _get_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False


def create_event(
    chunk_id: str,
    content: str,
    assigned_date: datetime,
    start_time_str: str,       # "09:00"
    time_period: int,          # hours
    urgency_level: int,
    goal_id: Optional[str] = None,
    reference_link: Optional[str] = None,
) -> Optional[str]:
    """
    Creates a Google Calendar event for an assigned task chunk.

    Returns the calendar event ID (stored on the TaskChunk for future updates/deletes).
    Returns None if calendar is not authorized — the assignment still succeeds,
    just without a calendar event.
    """
    if not is_authorized():
        print(f"[Calendar] Skipping event creation for {chunk_id} — not authorized.")
        return None

    try:
        service = _build_service()

        # Parse start datetime
        date_str = assigned_date.strftime("%Y-%m-%d")
        hour, minute = map(int, start_time_str.split(":"))
        start_dt = datetime(
            assigned_date.year, assigned_date.month, assigned_date.day,
            hour, minute, tzinfo=timezone.utc
        )
        end_dt = start_dt + timedelta(hours=time_period)

        # Build description
        description_parts = [f"Task Chunk: {chunk_id}"]
        if goal_id:
            description_parts.append(f"Goal: {goal_id}")
        if reference_link:
            description_parts.append(f"Reference: {reference_link}")

        event_body = {
            "summary": f"[{chunk_id}] {content[:80]}",
            "description": "\n".join(description_parts),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC",
            },
            "colorId": URGENCY_COLOR_MAP.get(urgency_level, "7"),
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                ],
            },
        }

        created = service.events().insert(
            calendarId="primary", body=event_body
        ).execute()

        event_id = created.get("id")
        print(f"[Calendar] Event created for {chunk_id}: {event_id}")
        return event_id

    except HttpError as e:
        print(f"[Calendar] Failed to create event for {chunk_id}: {e}")
        return None
    except Exception as e:
        print(f"[Calendar] Unexpected error for {chunk_id}: {e}")
        return None


def update_event(
    event_id: str,
    chunk_id: str,
    content: str,
    assigned_date: datetime,
    start_time_str: str,
    time_period: int,
    urgency_level: int,
) -> bool:
    """
    Updates an existing calendar event when a task chunk's schedule changes.
    Returns True on success, False on failure.
    """
    if not is_authorized():
        return False

    try:
        service = _build_service()

        hour, minute = map(int, start_time_str.split(":"))
        start_dt = datetime(
            assigned_date.year, assigned_date.month, assigned_date.day,
            hour, minute, tzinfo=timezone.utc
        )
        end_dt = start_dt + timedelta(hours=time_period)

        patch_body = {
            "summary": f"[{chunk_id}] {content[:80]}",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "UTC"},
            "colorId": URGENCY_COLOR_MAP.get(urgency_level, "7"),
        }

        service.events().patch(
            calendarId="primary", eventId=event_id, body=patch_body
        ).execute()

        print(f"[Calendar] Event updated for {chunk_id}: {event_id}")
        return True

    except HttpError as e:
        print(f"[Calendar] Failed to update event {event_id}: {e}")
        return False


def delete_event(event_id: str, chunk_id: str) -> bool:
    """
    Deletes a calendar event when a task chunk is cancelled or unassigned.
    Returns True on success, False on failure.
    """
    if not is_authorized():
        return False

    try:
        service = _build_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        print(f"[Calendar] Event deleted for {chunk_id}: {event_id}")
        return True

    except HttpError as e:
        print(f"[Calendar] Failed to delete event {event_id}: {e}")
        return False


def mark_event_complete(event_id: str, chunk_id: str) -> bool:
    """
    Adds a ✓ prefix to the event title when a task chunk is completed.
    """
    if not is_authorized():
        return False

    try:
        service = _build_service()

        # Fetch current event to get the title
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        current_summary = event.get("summary", "")

        if not current_summary.startswith("✓"):
            service.events().patch(
                calendarId="primary",
                eventId=event_id,
                body={"summary": f"✓ {current_summary}"},
            ).execute()

        print(f"[Calendar] Event marked complete for {chunk_id}: {event_id}")
        return True

    except HttpError as e:
        print(f"[Calendar] Failed to mark event complete {event_id}: {e}")
        return False

