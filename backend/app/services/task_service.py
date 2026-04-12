"""
services/task_service.py

Business logic for task chunk lifecycle. This is where the rules from
the spec document are implemented as Python functions. The API layer
is thin — it just calls these functions.

Key rules implemented here:
- Auto-generate REF-XXXX IDs
- Map urgency labels to internal integers
- Create the first StatusHistory entry on creation
- Handle BREACH acknowledgment (level degradation)
- Compute dashboard counters
- Sort To-Be-Assigned list by urgency then creation time
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.task_chunk import TaskChunk
from app.models.status_history import StatusHistory
from app.models.goal import Goal
from app.schemas.task_chunk import (
    TaskChunkCreate,
    TaskChunkUpdate,
    TaskChunkAssign,
    DashboardRead,
    URGENCY_INT_TO_LABEL,
    URGENCY_LABEL_TO_INT,
)

def _ensure_aware(dt: datetime) -> datetime:
    """
    Guarantees a datetime is timezone-aware (UTC).

    PostgreSQL always returns timezone-aware datetimes when the column uses
    DateTime(timezone=True). SQLite does not — it stores plain strings and
    returns naive datetimes. This helper normalises both so we never get a
    TypeError when subtracting two datetimes.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# --- Breach window per urgency level (in hours) ---
BREACH_WINDOWS = {
    2: 72,    # High: 3 days
    3: 72,    # Medium: 3 days
    4: 168,   # Low: 7 days
    5: None,  # Very Low: no timer
}

# Status constants
STATUS_OK = "OK"
STATUS_BREACH = "BREACH"
STATUS_BREACH_ACTION = "BREACH_ACTION"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"


# ---------------------------------------------------------------------------
# ID Generation
# ---------------------------------------------------------------------------

def _generate_chunk_id(db: Session) -> str:
    """
    Generates the next REF-XXXX id by looking at the highest existing number.
    Thread-safe enough for single-user use; a production system would use a
    DB sequence instead.
    """
    # Find the largest existing numeric suffix
    all_ids = db.query(TaskChunk.chunk_id).all()
    max_num = 0
    for (cid,) in all_ids:
        try:
            num = int(cid.split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue
    return f"REF-{max_num + 1:04d}"   # zero-padded to 4 digits: REF-0001


def _generate_goal_id(db: Session) -> str:
    """Generates the next GOAL-XXX id."""
    all_ids = db.query(Goal.goal_id).all()
    max_num = 0
    for (gid,) in all_ids:
        try:
            num = int(gid.split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue
    return f"GOAL-{max_num + 1:03d}"


# ---------------------------------------------------------------------------
# Status History Helper
# ---------------------------------------------------------------------------

def _record_history(
    db: Session,
    chunk_id: str,
    from_status: Optional[str],
    to_status: str,
    trigger: str,
    note: Optional[str] = None,
) -> None:
    """Appends one immutable row to the status_history table."""
    entry = StatusHistory(
        chunk_id=chunk_id,
        from_status=from_status,
        to_status=to_status,
        trigger=trigger,
        note=note,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)


# ---------------------------------------------------------------------------
# Goal CRUD
# ---------------------------------------------------------------------------

def create_goal(db: Session, title: str, description: Optional[str] = None) -> Goal:
    goal_id = _generate_goal_id(db)
    goal = Goal(goal_id=goal_id, title=title, description=description)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_all_goals(db: Session) -> List[Goal]:
    return db.query(Goal).order_by(Goal.created_at).all()


def get_goal(db: Session, goal_id: str) -> Optional[Goal]:
    return db.query(Goal).filter(Goal.goal_id == goal_id).first()


def update_goal(db: Session, goal_id: str, title: Optional[str], description: Optional[str]) -> Optional[Goal]:
    goal = get_goal(db, goal_id)
    if not goal:
        return None
    if title is not None:
        goal.title = title
    if description is not None:
        goal.description = description
    db.commit()
    db.refresh(goal)
    return goal


# ---------------------------------------------------------------------------
# TaskChunk CRUD
# ---------------------------------------------------------------------------

def create_task_chunk(db: Session, data: TaskChunkCreate) -> TaskChunk:
    """
    Creates a task chunk, sets initial status, and writes the first history entry.

    Special rule (Section 4): if urgency is Very High (level 1),
    the chunk is immediately moved to IN_PROGRESS status.
    """
    chunk_id = _generate_chunk_id(db)
    urgency_level = URGENCY_LABEL_TO_INT[data.urgency_label]

    # Very High urgency skips the waiting list entirely
    initial_status = STATUS_IN_PROGRESS if urgency_level == 1 else STATUS_OK

    chunk = TaskChunk(
        chunk_id=chunk_id,
        content=data.content,
        time_period=data.time_period,
        time_divergent=data.time_divergent or 0,
        urgency_level=urgency_level,
        status=initial_status,
        goal_id=data.goal_id,
        reference_link=data.reference_link,
    )
    db.add(chunk)
    db.flush()  # flush to get chunk into DB before writing history (FK requirement)

    _record_history(
        db, chunk_id,
        from_status=None,
        to_status=initial_status,
        trigger="CREATED",
        note=f"Task chunk created with urgency: {data.urgency_label}",
    )

    db.commit()
    db.refresh(chunk)
    return chunk


def get_task_chunk(db: Session, chunk_id: str) -> Optional[TaskChunk]:
    return db.query(TaskChunk).filter(TaskChunk.chunk_id == chunk_id).first()


def get_to_be_assigned(db: Session) -> List[TaskChunk]:
    """
    Returns the To-Be-Assigned list: chunks with status OK/BREACH/BREACH_ACTION,
    sorted by urgency (ascending = highest first), then by created_at (ascending).
    """
    return (
        db.query(TaskChunk)
        .filter(
            TaskChunk.status.in_([STATUS_OK, STATUS_BREACH, STATUS_BREACH_ACTION]),
            TaskChunk.is_archived == False,
        )
        .order_by(TaskChunk.urgency_level.asc(), TaskChunk.created_at.asc())
        .all()
    )


def get_assigned(db: Session) -> List[TaskChunk]:
    """Returns all chunks currently in progress."""
    return (
        db.query(TaskChunk)
        .filter(TaskChunk.status == STATUS_IN_PROGRESS, TaskChunk.is_archived == False)
        .order_by(TaskChunk.assigned_date.asc())
        .all()
    )


def update_task_chunk(db: Session, chunk_id: str, data: TaskChunkUpdate) -> Optional[TaskChunk]:
    """Updates mutable fields. Records history if status changes."""
    chunk = get_task_chunk(db, chunk_id)
    if not chunk:
        return None

    old_status = chunk.status

    if data.content is not None:
        chunk.content = data.content
    if data.time_period is not None:
        chunk.time_period = data.time_period
    if data.time_divergent is not None:
        chunk.time_divergent = data.time_divergent
    if data.urgency_label is not None:
        chunk.urgency_level = URGENCY_LABEL_TO_INT[data.urgency_label]
    if data.goal_id is not None:
        chunk.goal_id = data.goal_id
    if data.reference_link is not None:
        chunk.reference_link = data.reference_link
    if data.status is not None and data.status != old_status:
        chunk.status = data.status
        _record_history(db, chunk_id, old_status, data.status, "MANUAL_UPDATE")

    chunk.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(chunk)
    return chunk


def assign_task_chunk(db: Session, chunk_id: str, data: TaskChunkAssign) -> Optional[TaskChunk]:
    """Moves a chunk from To-Be-Assigned to Assigned (IN_PROGRESS)."""
    chunk = get_task_chunk(db, chunk_id)
    if not chunk:
        return None

    old_status = chunk.status
    chunk.status = STATUS_IN_PROGRESS
    chunk.assigned_date = data.assigned_date
    chunk.start_time = data.start_time
    chunk.updated_at = datetime.now(timezone.utc)

    _record_history(
        db, chunk_id, old_status, STATUS_IN_PROGRESS,
        trigger="MANUAL_ASSIGN",
        note=data.note,
    )

    db.commit()
    db.refresh(chunk)
    return chunk


def acknowledge_breach(db: Session, chunk_id: str) -> Optional[TaskChunk]:
    """
    User ACK on a breached task chunk (Section 5.2 of spec).
    Degrades urgency by one level (e.g. High → Medium).
    Level 5 is the terminal state — no further degradation.
    """
    chunk = get_task_chunk(db, chunk_id)
    if not chunk:
        return None

    old_level = chunk.urgency_level
    new_level = min(old_level + 1, 5)  # never go below Very Low
    old_status = chunk.status

    chunk.urgency_level = new_level
    chunk.status = STATUS_OK
    chunk.updated_at = datetime.now(timezone.utc)

    new_label = URGENCY_INT_TO_LABEL[new_level]
    _record_history(
        db, chunk_id, old_status, STATUS_OK,
        trigger="USER_ACK",
        note=f"Urgency degraded from level {old_level} to {new_level} ({new_label})",
    )

    db.commit()
    db.refresh(chunk)
    return chunk


def complete_task_chunk(db: Session, chunk_id: str, note: Optional[str] = None) -> Optional[TaskChunk]:
    """Marks a chunk as COMPLETED."""
    chunk = get_task_chunk(db, chunk_id)
    if not chunk:
        return None

    old_status = chunk.status
    chunk.status = STATUS_COMPLETED
    chunk.updated_at = datetime.now(timezone.utc)
    _record_history(db, chunk_id, old_status, STATUS_COMPLETED, "COMPLETED", note)

    db.commit()
    db.refresh(chunk)
    return chunk


def fail_task_chunk(db: Session, chunk_id: str, note: Optional[str] = None) -> Optional[TaskChunk]:
    """Marks a chunk as FAILED."""
    chunk = get_task_chunk(db, chunk_id)
    if not chunk:
        return None

    old_status = chunk.status
    chunk.status = STATUS_FAILED
    chunk.updated_at = datetime.now(timezone.utc)
    _record_history(db, chunk_id, old_status, STATUS_FAILED, "FAILED", note)

    db.commit()
    db.refresh(chunk)
    return chunk


def search_task_chunks(
    db: Session,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    urgency_label: Optional[str] = None,
    goal_id: Optional[str] = None,
) -> List[TaskChunk]:
    """Full-text and filter search over all task chunks (Section 7 of spec)."""
    query = db.query(TaskChunk)

    if keyword:
        query = query.filter(
            TaskChunk.content.ilike(f"%{keyword}%")
            | TaskChunk.chunk_id.ilike(f"%{keyword}%")
        )
    if status:
        query = query.filter(TaskChunk.status == status)
    if urgency_label:
        level = URGENCY_LABEL_TO_INT.get(urgency_label)
        if level:
            query = query.filter(TaskChunk.urgency_level == level)
    if goal_id:
        query = query.filter(TaskChunk.goal_id == goal_id)

    return query.order_by(TaskChunk.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Timer / Breach Checker (called by background scheduler)
# ---------------------------------------------------------------------------

def check_and_apply_breaches(db: Session) -> int:
    """
    Scans all OK chunks in the waiting list and promotes them to BREACH
    or BREACH_ACTION if they have exceeded their urgency window.

    Returns the number of chunks updated.
    Called by the APScheduler background job in main.py.
    """
    now = datetime.now(timezone.utc)
    updated = 0

    waiting_chunks = (
        db.query(TaskChunk)
        .filter(TaskChunk.status == STATUS_OK, TaskChunk.is_archived == False)
        .all()
    )

    for chunk in waiting_chunks:
        window_hours = BREACH_WINDOWS.get(chunk.urgency_level)
        if window_hours is None:
            continue  # Very Low — no timer

        age_hours = (now - _ensure_aware(chunk.created_at)).total_seconds() / 3600
        if age_hours >= window_hours:
            old_status = chunk.status
            new_status = STATUS_BREACH_ACTION if chunk.urgency_level == 2 else STATUS_BREACH
            chunk.status = new_status
            chunk.updated_at = now
            _record_history(
                db, chunk.chunk_id, old_status, new_status,
                trigger="TIMER",
                note=f"Breach window of {window_hours}h exceeded after {age_hours:.1f}h",
            )
            updated += 1

    if updated > 0:
        db.commit()

    return updated


# ---------------------------------------------------------------------------
# Dashboard Counters
# ---------------------------------------------------------------------------

def get_dashboard(db: Session) -> DashboardRead:
    """Computes system-wide counters (Section 6 of spec)."""

    def count(status_val):
        return db.query(TaskChunk).filter(TaskChunk.status == status_val).count()

    waiting = (
        db.query(TaskChunk)
        .filter(TaskChunk.status.in_([STATUS_OK, STATUS_BREACH, STATUS_BREACH_ACTION]))
        .count()
    )
    breached = (
        db.query(TaskChunk)
        .filter(TaskChunk.status.in_([STATUS_BREACH, STATUS_BREACH_ACTION]))
        .count()
    )

    # Average waiting time: for completed/in-progress chunks, measure created_at → assigned_date
    completed_with_assigned = (
        db.query(TaskChunk)
        .filter(TaskChunk.assigned_date.isnot(None))
        .all()
    )
    if completed_with_assigned:
        total_hours = sum(
            (_ensure_aware(c.assigned_date) - _ensure_aware(c.created_at)).total_seconds() / 3600
            for c in completed_with_assigned
        )
        avg_waiting = round(total_hours / len(completed_with_assigned), 2)
    else:
        avg_waiting = None

    return DashboardRead(
        waiting=waiting,
        in_progress=count(STATUS_IN_PROGRESS),
        completed=count(STATUS_COMPLETED),
        failed=count(STATUS_FAILED),
        breached=breached,
        avg_waiting_hours=avg_waiting,
    )


# ---------------------------------------------------------------------------
# Urgency label helper (used by API layer to enrich TaskChunk objects)
# ---------------------------------------------------------------------------

def enrich_urgency_label(chunk: TaskChunk) -> dict:
    """Returns a dict representation of the chunk with urgency_label added."""
    data = {c.name: getattr(chunk, c.name) for c in chunk.__table__.columns}
    data["urgency_label"] = URGENCY_INT_TO_LABEL.get(chunk.urgency_level, "Unknown")
    data["status_history"] = chunk.status_history
    return data
