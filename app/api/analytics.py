from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User
from app.application.services.analytics_service import AnalyticsService
from app.application.services.instructor_analytics_service import InstructorAnalyticsService
from app.schemas.analytics_schema import LearnerAnalyticsResponse, InstructorCohortScoresResponse

router = APIRouter()


@router.get("/learner/scores", response_model=LearnerAnalyticsResponse)
def get_learner_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_learner_scores(db, current_user)


@router.get("/instructor/cohort/{cohort_id}/scores", response_model=InstructorCohortScoresResponse)
def get_instructor_cohort_scores(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InstructorAnalyticsService.get_cohort_scores(db, cohort_id, current_user)