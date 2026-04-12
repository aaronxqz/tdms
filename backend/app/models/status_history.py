"""
models/status_history.py

Immutable audit log of every status change for every task chunk
(Section 5.3 of the spec). Rows are never updated — only inserted.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(
        String(20),
        ForeignKey("task_chunks.chunk_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status = Column(String(20), nullable=True)   # null for the very first entry (creation)
    to_status = Column(String(20), nullable=False)
    trigger = Column(String(50), nullable=False)       # e.g. CREATED | USER_ACK | TIMER | MANUAL_ASSIGN
    note = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to the parent task chunk
    task_chunk = relationship("TaskChunk", back_populates="status_history")