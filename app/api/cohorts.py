from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User
from app.application.services.cohort_learning_service import CohortLearningService
from app.schemas.cohort_schema import (
    AssignLearningRequest,
    AssignLearningResponse,
    CohortLearningResponse,
)

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])


@router.get("/{cohort_id}/learning", response_model=CohortLearningResponse)
def get_cohort_learning(
    cohort_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CohortLearningService.get_learning(db, cohort_id, current_user)


@router.post("/{cohort_id}/learning", response_model=AssignLearningResponse, status_code=201)
def assign_learning(
    cohort_id: int,
    payload: AssignLearningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CohortLearningService.assign_learning(db, cohort_id, payload, current_user)


@router.delete("/{cohort_id}/learning/{assignment_id}")
def remove_learning(
    cohort_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CohortLearningService.remove_learning(db, cohort_id, assignment_id, current_user)
