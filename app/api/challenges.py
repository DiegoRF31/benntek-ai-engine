from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_challenges():
    return {"message": "Challenges endpoint working"}