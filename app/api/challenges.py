from fastapi import APIRouter, Depends
from app.api.auth import get_current_user
from app.infrastructure.models.user_model import User

router = APIRouter()

@router.get("/")
def list_challenges(current_user: User = Depends(get_current_user)):
    return {"message": "Challenges endpoint working"}