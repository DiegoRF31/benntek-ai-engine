from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.infrastructure.models.submission_model import Submission
from app.application.use_cases.submit_challenge_use_case import SubmitChallengeUseCase
from app.schemas.submission_schema import SubmissionCreate  # si ya existe

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("/")
def submit_challenge(
    data: SubmissionCreate,
    db: Session = Depends(get_db)
):

    submission = Submission(**data.dict())

    db.add(submission)
    db.flush()  

    score = SubmitChallengeUseCase.execute(db, submission)

    return {"score": score}