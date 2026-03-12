from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User
from app.application.services.analytics_service import AnalyticsService
from app.schemas.analytics_schema import LearnerAnalyticsResponse

router = APIRouter()


@router.get("/learner/scores", response_model=LearnerAnalyticsResponse)
def get_learner_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_learner_scores(db, current_user)