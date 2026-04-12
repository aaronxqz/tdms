"""
api/tasks.py

HTTP endpoints for TaskChunk lifecycle management.

Endpoint map:
  POST   /tasks/                     → create task chunk
  GET    /tasks/waiting              → to-be-assigned list
  GET    /tasks/assigned             → assigned / in-progress list
  GET    /tasks/search               → search all chunks
  GET    /tasks/dashboard            → system-wide counters
  GET    /tasks/{chunk_id}           → single chunk detail
  PATCH  /tasks/{chunk_id}           → update fields
  POST   /tasks/{chunk_id}/assign    → assign (move to in-progress)
  POST   /tasks/{chunk_id}/ack       → acknowledge breach (degrade urgency)
  POST   /tasks/{chunk_id}/complete  → mark completed
  POST   /tasks/{chunk_id}/fail      → mark failed
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import calendar_service
from app.schemas.task_chunk import (
    TaskChunkCreate,
    TaskChunkUpdate,
    TaskChunkAssign,
    TaskChunkRead,
    DashboardRead,
    URGENCY_INT_TO_LABEL,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _to_read(chunk) -> TaskChunkRead:
    """
    Helper: converts a TaskChunk ORM object to a TaskChunkRead schema.
    Adds the urgency_label field that doesn't exist on the raw model.
    """
    return TaskChunkRead(
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        time_period=chunk.time_period,
        time_divergent=chunk.time_divergent,
        urgency_level=chunk.urgency_level,
        urgency_label=URGENCY_INT_TO_LABEL.get(chunk.urgency_level, "Unknown"),
        status=chunk.status,
        goal_id=chunk.goal_id,
        reference_link=chunk.reference_link,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
        assigned_date=chunk.assigned_date,
        start_time=chunk.start_time,
        calendar_event_id=chunk.calendar_event_id,
        status_history=chunk.status_history,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("/", response_model=TaskChunkRead, status_code=status.HTTP_201_CREATED)
def create_task_chunk(data: TaskChunkCreate, db: Session = Depends(get_db)):
    """
    Creates a new task chunk and places it in the To-Be-Assigned list.
    If urgency is Very High, it immediately moves to IN_PROGRESS.
    """
    chunk = task_service.create_task_chunk(db, data)
    return _to_read(chunk)


# ---------------------------------------------------------------------------
# List views
# ---------------------------------------------------------------------------

@router.get("/waiting", response_model=List[TaskChunkRead])
def get_waiting_list(db: Session = Depends(get_db)):
    """
    Returns the To-Be-Assigned list sorted by urgency (highest first),
    then by creation time (earliest first). Very High chunks are not shown
    here — they go straight to IN_PROGRESS.
    """
    chunks = task_service.get_to_be_assigned(db)
    return [_to_read(c) for c in chunks]


@router.get("/assigned", response_model=List[TaskChunkRead])
def get_assigned_list(db: Session = Depends(get_db)):
    """Returns all currently in-progress chunks sorted by assigned date."""
    chunks = task_service.get_assigned(db)
    return [_to_read(c) for c in chunks]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search", response_model=List[TaskChunkRead])
def search(
    keyword: Optional[str] = Query(None, description="Search in content or chunk_id"),
    status: Optional[str] = Query(None, description="Filter by status"),
    urgency_label: Optional[str] = Query(None, description="Filter by urgency label"),
    goal_id: Optional[str] = Query(None, description="Filter by goal"),
    db: Session = Depends(get_db),
):
    """
    Search across all task chunks (including historical ones).
    All query parameters are optional and combinable.
    Example: GET /tasks/search?keyword=graph&status=OK
    """
    chunks = task_service.search_task_chunks(db, keyword, status, urgency_label, goal_id)
    return [_to_read(c) for c in chunks]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardRead)
def get_dashboard(db: Session = Depends(get_db)):
    """Returns system-wide aggregate counters."""
    return task_service.get_dashboard(db)


# ---------------------------------------------------------------------------
# Single chunk operations
# ---------------------------------------------------------------------------

@router.get("/{chunk_id}", response_model=TaskChunkRead)
def get_task_chunk(chunk_id: str, db: Session = Depends(get_db)):
    chunk = task_service.get_task_chunk(db, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return _to_read(chunk)


@router.patch("/{chunk_id}", response_model=TaskChunkRead)
def update_task_chunk(chunk_id: str, data: TaskChunkUpdate, db: Session = Depends(get_db)):
    """Update any mutable field on a task chunk."""
    chunk = task_service.update_task_chunk(db, chunk_id, data)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    return _to_read(chunk)


@router.post("/{chunk_id}/assign", response_model=TaskChunkRead)
def assign_task_chunk(chunk_id: str, data: TaskChunkAssign, db: Session = Depends(get_db)):
    """
    Moves a task chunk to the Assigned list (IN_PROGRESS).
    Also creates a Google Calendar event if authorized.
    """
    chunk = task_service.assign_task_chunk(db, chunk_id, data)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")

    # Create Google Calendar event (fails silently if not authorized)
    if chunk.assigned_date and chunk.start_time:
        event_id = calendar_service.create_event(
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            assigned_date=chunk.assigned_date,
            start_time_str=chunk.start_time,
            time_period=chunk.time_period,
            urgency_level=chunk.urgency_level,
            goal_id=chunk.goal_id,
            reference_link=chunk.reference_link,
        )
        if event_id:
            chunk.calendar_event_id = event_id
            db.commit()
            db.refresh(chunk)

    return _to_read(chunk)


@router.post("/{chunk_id}/ack", response_model=TaskChunkRead)
def acknowledge_breach(chunk_id: str, db: Session = Depends(get_db)):
    """
    User acknowledges a BREACH or BREACH_ACTION alert.
    Degrades urgency by one level and resets status to OK.
    """
    chunk = task_service.get_task_chunk(db, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")
    if chunk.status not in ("BREACH", "BREACH_ACTION"):
        raise HTTPException(
            status_code=400,
            detail=f"Chunk {chunk_id} is not in a breach state (current: {chunk.status})",
        )
    chunk = task_service.acknowledge_breach(db, chunk_id)
    return _to_read(chunk)


@router.post("/{chunk_id}/complete", response_model=TaskChunkRead)
def complete_task_chunk(
    chunk_id: str,
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Marks a task chunk as COMPLETED. Adds checkmark prefix to calendar event."""
    chunk = task_service.complete_task_chunk(db, chunk_id, note)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")

    if chunk.calendar_event_id:
        calendar_service.mark_event_complete(chunk.calendar_event_id, chunk_id)

    return _to_read(chunk)


@router.post("/{chunk_id}/fail", response_model=TaskChunkRead)
def fail_task_chunk(
    chunk_id: str,
    note: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Marks a task chunk as FAILED. Deletes the calendar event if one exists."""
    chunk = task_service.fail_task_chunk(db, chunk_id, note)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")

    if chunk.calendar_event_id:
        calendar_service.delete_event(chunk.calendar_event_id, chunk_id)

    return _to_read(chunk)