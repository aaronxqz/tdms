"""
models/task_chunk.py

Core entity of the system. Represents one task chunk in either the
To-Be-Assigned list or the Assigned list (Section 3 of the spec).

Urgency is stored as an integer (1-5) internally.
The API layer maps it to/from human labels (Very High / High / etc.)
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class TaskChunk(Base):
    __tablename__ = "task_chunks"

    # --- Identity ---
    chunk_id = Column(String(20), primary_key=True)      # e.g. "REF-0042"
    goal_id = Column(String(20), ForeignKey("goals.goal_id"), nullable=True)

    # --- Content ---
    content = Column(Text, nullable=False)
    reference_link = Column(Text, nullable=True)

    # --- Time estimate ---
    time_period = Column(Integer, nullable=False)         # in hours
    time_divergent = Column(Integer, nullable=False, default=0)

    # --- Urgency & Status ---
    urgency_level = Column(Integer, nullable=False, default=4)  # 1=Very High … 5=Very Low
    status = Column(String(20), nullable=False, default="OK")
    # Possible values: OK | BREACH | BREACH_ACTION | IN_PROGRESS | COMPLETED | FAILED

    # --- Timestamps ---
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- Assignment fields (populated when moved to Assigned list) ---
    assigned_date = Column(DateTime(timezone=True), nullable=True)
    start_time = Column(String(10), nullable=True)        # e.g. "09:00"
    calendar_event_id = Column(String(200), nullable=True)

    # --- Soft delete / archive ---
    is_archived = Column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    goal = relationship("Goal", back_populates="task_chunks")
    status_history = relationship(
        "StatusHistory",
        back_populates="task_chunk",
        order_by="StatusHistory.timestamp",  # always retrieve history in chronological order
        cascade="all, delete-orphan",        # delete history entries when chunk is deleted
    )