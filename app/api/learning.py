from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User
from app.application.services.learning_service import LearningService
from app.schemas.learning_schema import ModulesResponse, PathsResponse

router = APIRouter(
    prefix="/learning",
    tags=["Learning"],
)


@router.get("/modules", response_model=ModulesResponse)
def get_modules(
    level: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningService.get_modules(db, current_user, level=level, search=search)


@router.get("/paths", response_model=PathsResponse)
def get_paths(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningService.get_paths(db, current_user)
