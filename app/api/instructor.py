from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user, require_role
from app.infrastructure.models.user_model import User
from app.application.services.cohort_service import CohortService
from app.application.services.challenge_authoring_service import ChallengeAuthoringService
from app.schemas.cohort_schema import (
    CohortsResponse,
    CohortCreateRequest,
    CohortCreateResponse,
    CohortDetailResponse,
    AssignChallengeRequest,
    EnrollStudentRequest,
    AvailableChallengesResponse,
    AvailableStudentsResponse,
    InstructorAnalyticsResponse,
)
from app.schemas.challenge_authoring_schema import (
    InstructorChallengesResponse,
    CreateChallengeRequest,
    CreateChallengeResponse,
    GenerateDraftRequest,
    ApproveRequest,
    ApproveResponse,
    UpdateChallengeRequest,
    UpdateChallengeResponse,
)

router = APIRouter(
    prefix="/instructor",
    tags=["Instructor"],
)


# ===========================================================================
# Challenge Authoring  —  /instructor/challenges/...
# NOTE: literal-segment routes (create, generate, approve) must be declared
# before the parameterised route /{challenge_id} to avoid routing conflicts.
# ===========================================================================

@router.get("/challenges", response_model=InstructorChallengesResponse)
def get_instructor_challenges(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return ChallengeAuthoringService.get_challenges(db, current_user)


@router.post("/challenges/create", response_model=CreateChallengeResponse, status_code=status.HTTP_201_CREATED)
def create_challenge(
    payload: CreateChallengeRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return ChallengeAuthoringService.create_challenge(db, current_user, payload)


@router.post("/challenges/generate", response_model=CreateChallengeResponse, status_code=status.HTTP_201_CREATED)
def save_generated_draft(
    payload: GenerateDraftRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return ChallengeAuthoringService.generate_draft(db, current_user, payload)


@router.post("/challenges/approve/{challenge_id}", response_model=ApproveResponse)
def approve_challenge(
    challenge_id: int,
    payload: ApproveRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    return ChallengeAuthoringService.approve_challenge(db, current_user, challenge_id, payload)


@router.put("/challenges/{challenge_id}", response_model=UpdateChallengeResponse)
def update_challenge(
    challenge_id: int,
    payload: UpdateChallengeRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return ChallengeAuthoringService.update_challenge(db, current_user, challenge_id, payload)


@router.delete("/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_challenge(
    challenge_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    ChallengeAuthoringService.delete_challenge(db, current_user, challenge_id)


# ===========================================================================
# Cohort Management  —  /instructor/cohorts/...
# ===========================================================================

@router.get("/cohorts", response_model=CohortsResponse)
def get_cohorts(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return CohortService.get_cohorts(db, current_user)


@router.post("/cohorts", response_model=CohortCreateResponse, status_code=status.HTTP_201_CREATED)
def create_cohort(
    payload: CohortCreateRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return CohortService.create_cohort(db, current_user, payload)


@router.get("/cohorts/{cohort_id}", response_model=CohortDetailResponse)
def get_cohort_detail(
    cohort_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    result = CohortService.get_cohort_detail(db, current_user, cohort_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return result


@router.post("/cohorts/{cohort_id}/challenges", status_code=status.HTTP_201_CREATED)
def assign_challenge_to_cohort(
    cohort_id: int,
    payload: AssignChallengeRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    result = CohortService.assign_challenge(db, current_user, cohort_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return result


@router.post("/cohorts/{cohort_id}/students", status_code=status.HTTP_201_CREATED)
def enroll_student(
    cohort_id: int,
    payload: EnrollStudentRequest,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    result = CohortService.enroll_student(db, current_user, cohort_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return result


@router.get("/cohorts/{cohort_id}/available-challenges", response_model=AvailableChallengesResponse)
def get_available_challenges(
    cohort_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    result = CohortService.get_available_challenges(db, current_user, cohort_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return result


@router.get("/cohorts/{cohort_id}/available-students", response_model=AvailableStudentsResponse)
def get_available_students(
    cohort_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    result = CohortService.get_available_students(db, current_user, cohort_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return result


# ===========================================================================
# Instructor Analytics  —  /instructor/analytics
# ===========================================================================

@router.get("/analytics", response_model=InstructorAnalyticsResponse)
def get_analytics(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return CohortService.get_analytics(db, current_user)
