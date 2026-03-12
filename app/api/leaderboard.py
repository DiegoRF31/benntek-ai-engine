from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User
from app.application.services.leaderboard_service import LeaderboardService
from app.schemas.leaderboard_schema import (
    GlobalLeaderboardResponse,
    CohortLeaderboardResponse,
    CohortsResponse,
)

router = APIRouter(
    prefix="/leaderboard",
    tags=["Leaderboard"],
)


@router.get("/global", response_model=GlobalLeaderboardResponse)
def get_global_leaderboard(
    timeframe: str = Query(default="all-time", pattern="^(all-time|month|week)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LeaderboardService.get_global(db, current_user, timeframe, limit)


@router.get("/cohorts", response_model=CohortsResponse)
def get_cohorts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LeaderboardService.get_cohorts(db, current_user)


@router.get("/cohort/{cohort_id}", response_model=CohortLeaderboardResponse)
def get_cohort_leaderboard(
    cohort_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LeaderboardService.get_cohort(db, current_user, cohort_id, limit)
