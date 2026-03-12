from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.application.services.challenge_service import ChallengeService
from app.core.database import get_db
from app.infrastructure.models.user_model import User
from app.schemas.challenge_schema import (
    AssignedCohortResponse,
    ChallengeDetailResponse,
    ChallengeListResponse,
    ChallengeSubmissionCreate,
    ChallengeSubmissionResponse,
    HintsResponse,
    HintUnlockResponse,
    SolutionDownloadResponse,
    SubmissionHistoryResponse,
    TestResultsResponse,
)

router = APIRouter()


@router.get("/", response_model=ChallengeListResponse)
def list_challenges(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.list_challenges(
        db, current_user,
        search=search,
        category=category,
        difficulty=difficulty,
        challenge_type=type,
    )


@router.get("/assigned", response_model=AssignedCohortResponse)
def get_assigned(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.get_assigned(db, current_user)


@router.get("/{challenge_id}", response_model=ChallengeDetailResponse)
def get_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ChallengeService.get_challenge_detail(db, challenge_id, current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return result


@router.get("/{challenge_id}/submissions", response_model=SubmissionHistoryResponse)
def get_submission_history(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.get_submission_history(db, challenge_id, current_user)


@router.post("/{challenge_id}/submissions", response_model=ChallengeSubmissionResponse)
def create_submission(
    challenge_id: int,
    payload: ChallengeSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.create_submission(db, challenge_id, current_user, payload)


@router.get("/{challenge_id}/hints", response_model=HintsResponse)
def get_hints(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.get_hints(db, challenge_id, current_user)


@router.post("/{challenge_id}/hint/{hint_id}/unlock", response_model=HintUnlockResponse)
def unlock_hint(
    challenge_id: int,
    hint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.unlock_hint(db, challenge_id, hint_id, current_user)


@router.get("/{challenge_id}/test-results", response_model=TestResultsResponse)
def get_test_results(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.get_test_results(db, challenge_id, current_user)


@router.post("/{challenge_id}/solution/download", response_model=SolutionDownloadResponse)
def download_solution(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ChallengeService.get_solution_download(db, challenge_id, current_user)
