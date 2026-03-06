from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import require_role
from app.infrastructure.models.user_model import User

router = APIRouter(
    prefix="/instructor",
    tags=["Instructor"]
)

@router.get("/cohorts")
def get_cohorts(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db)
):
    
    return {
        "message": "Instructor cohorts endpoint working",
        "user": current_user.email,
        "role": current_user.role
    } 