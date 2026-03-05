from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.infrastructure.models.submission_model import Submission
from app.application.use_cases.submit_challenge_use_case import SubmitChallengeUseCase
from app.schemas.submission_schema import SubmissionCreate 
from app.api.auth import require_role
from app.infrastructure.models.user_model import User

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("/")
def submit_challenge(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["learner"]))
):

    submission = Submission(
    tenant_id=current_user.tenant_id,
    user_id=current_user.id,
    challenge_version_id=data.challenge_version_id,
    input_text=data.input_text,
    attempt_number=data.attempt_number
)

    db.add(submission)
    db.flush()  

    score = SubmitChallengeUseCase.execute(db, submission)

    return {"score": score}