"""
models/goal.py

Represents the Goal Registry (Section 2.2 of the spec).
A Goal is the parent container for one or more TaskChunks.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class Goal(Base):
    __tablename__ = "goals"

    goal_id = Column(String(20), primary_key=True)       # e.g. "GOAL-001"
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # One Goal → many TaskChunks
    # 'back_populates' creates a .goal attribute on each TaskChunk
    task_chunks = relationship("TaskChunk", back_populates="goal")