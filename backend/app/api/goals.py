"""
api/goals.py

HTTP endpoints for Goal management.
Routes are thin by design — they validate input (Pydantic does this
automatically), call a service function, and return the result.
No business logic lives here.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.goal import GoalCreate, GoalRead, GoalUpdate
from app.services import task_service

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.post("/", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(data: GoalCreate, db: Session = Depends(get_db)):
    """Create a new goal. goal_id is auto-generated."""
    return task_service.create_goal(db, title=data.title, description=data.description)


@router.get("/", response_model=List[GoalRead])
def list_goals(db: Session = Depends(get_db)):
    """Return all goals ordered by creation date."""
    return task_service.get_all_goals(db)


@router.get("/{goal_id}", response_model=GoalRead)
def get_goal(goal_id: str, db: Session = Depends(get_db)):
    goal = task_service.get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalRead)
def update_goal(goal_id: str, data: GoalUpdate, db: Session = Depends(get_db)):
    """Update title and/or description of an existing goal."""
    goal = task_service.update_goal(db, goal_id, data.title, data.description)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return goal