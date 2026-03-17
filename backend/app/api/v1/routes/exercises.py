from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.schemas import ExerciseAttemptIn, ExerciseAttemptOut, ExerciseDetail, ExerciseOut
from app.services.exercise_service import create_attempt, get_exercise_detail, list_exercises, recommended_exercises

router = APIRouter(prefix="/exercises", tags=["exercises"])


def get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1))


@router.get("", response_model=List[ExerciseOut])
def get_exercises(
    category: Optional[str] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[ExerciseOut]:
    return [ExerciseOut.model_validate(exercise) for exercise in list_exercises(db, category, difficulty, search)]


@router.get("/recommended", response_model=List[ExerciseOut])
def get_recommended(db: Session = Depends(get_db)) -> List[ExerciseOut]:
    return [ExerciseOut.model_validate(exercise) for exercise in recommended_exercises(db)]


@router.get("/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseDetail:
    detail = get_exercise_detail(db, exercise_id, get_user_id(db))
    if not detail:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ExerciseDetail(
        exercise=ExerciseOut.model_validate(detail["exercise"]),
        attempts=[ExerciseAttemptOut.model_validate(item) for item in detail["attempts"]],
    )


@router.post("/{exercise_id}/attempt", response_model=ExerciseAttemptOut)
def submit_attempt(exercise_id: int, payload: ExerciseAttemptIn, db: Session = Depends(get_db)) -> ExerciseAttemptOut:
    return ExerciseAttemptOut.model_validate(
        create_attempt(db, exercise_id, get_user_id(db), payload.submitted_code, payload.notes)
    )
