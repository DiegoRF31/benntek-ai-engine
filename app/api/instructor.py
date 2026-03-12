from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import require_role
from app.infrastructure.models.user_model import User
from app.application.services.cohort_service import CohortService
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

router = APIRouter(
    prefix="/instructor",
    tags=["Instructor"],
)


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
def assign_challenge(
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


@router.get("/analytics", response_model=InstructorAnalyticsResponse)
def get_analytics(
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    return CohortService.get_analytics(db, current_user)
