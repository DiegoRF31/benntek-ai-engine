from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.infrastructure.models.user_model import User
from app.infrastructure.models.cohort_model import Cohort
from app.infrastructure.models.cohort_learning_assignment_model import CohortLearningAssignment
from app.infrastructure.models.learning_path_model import PathModule
from app.schemas.cohort_schema import (
    AssignLearningRequest,
    AssignLearningResponse,
    LearningAssignmentPathItem,
    LearningAssignmentModuleItem,
    CohortLearningResponse,
)

_INSTRUCTOR_ROLES = {"instructor", "admin"}


def _fmt_date(d) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.isoformat()


def _require_cohort(db: Session, cohort_id: int, tenant_id: int) -> Cohort:
    cohort = db.query(Cohort).filter(
        Cohort.id == cohort_id,
        Cohort.tenant_id == tenant_id,
    ).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return cohort


class CohortLearningService:

    @staticmethod
    def get_learning(
        db: Session,
        cohort_id: int,
        current_user: User,
    ) -> CohortLearningResponse:
        _require_cohort(db, cohort_id, current_user.tenant_id)

        assignments = (
            db.query(CohortLearningAssignment)
            .filter(CohortLearningAssignment.cohort_id == cohort_id)
            .order_by(CohortLearningAssignment.assigned_at)
            .all()
        )

        path_items: list[LearningAssignmentPathItem] = []
        module_items: list[LearningAssignmentModuleItem] = []

        for a in assignments:
            assigner_username = (
                a.assigned_by.username if a.assigned_by and hasattr(a.assigned_by, "username")
                else (a.assigned_by.email.split("@")[0] if a.assigned_by else None)
            )

            if a.learning_path_id and a.learning_path:
                path = a.learning_path
                # Count modules in this path
                module_count = (
                    db.query(PathModule)
                    .filter(PathModule.path_id == path.id)
                    .count()
                )
                path_items.append(
                    LearningAssignmentPathItem(
                        assignment_id=a.id,
                        title=path.title,
                        level=path.level,
                        description=path.description,
                        is_required=a.is_required,
                        due_date=_fmt_date(a.due_date),
                        assigned_at=_fmt_date(a.assigned_at),
                        assigned_by_username=assigner_username,
                        module_count=module_count,
                        estimated_hours=path.estimated_hours,
                    )
                )
            elif a.module_id and a.module:
                mod = a.module
                module_items.append(
                    LearningAssignmentModuleItem(
                        assignment_id=a.id,
                        title=mod.title,
                        level=mod.level,
                        summary=mod.summary,
                        is_required=a.is_required,
                        due_date=_fmt_date(a.due_date),
                        assigned_at=_fmt_date(a.assigned_at),
                        assigned_by_username=assigner_username,
                        estimated_minutes=mod.estimated_minutes,
                    )
                )

        return CohortLearningResponse(paths=path_items, modules=module_items)

    @staticmethod
    def assign_learning(
        db: Session,
        cohort_id: int,
        payload: AssignLearningRequest,
        current_user: User,
    ) -> AssignLearningResponse:
        if current_user.role not in _INSTRUCTOR_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instructor access required")

        _require_cohort(db, cohort_id, current_user.tenant_id)

        if not payload.learning_path_id and not payload.module_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either learning_path_id or module_id is required",
            )
        if payload.learning_path_id and payload.module_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide only one of learning_path_id or module_id",
            )

        # Check for duplicates
        existing_q = db.query(CohortLearningAssignment).filter(
            CohortLearningAssignment.cohort_id == cohort_id
        )
        if payload.learning_path_id:
            existing_q = existing_q.filter(
                CohortLearningAssignment.learning_path_id == payload.learning_path_id
            )
        else:
            existing_q = existing_q.filter(
                CohortLearningAssignment.module_id == payload.module_id
            )
        if existing_q.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This content is already assigned to the cohort",
            )

        due_date: Optional[date] = None
        if payload.due_date:
            try:
                due_date = date.fromisoformat(payload.due_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid due_date format, expected YYYY-MM-DD",
                )

        assignment = CohortLearningAssignment(
            cohort_id=cohort_id,
            learning_path_id=payload.learning_path_id,
            module_id=payload.module_id,
            assigned_by_id=current_user.id,
            due_date=due_date,
            is_required=payload.is_required,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        return AssignLearningResponse(success=True, assignment_id=assignment.id)

    @staticmethod
    def remove_learning(
        db: Session,
        cohort_id: int,
        assignment_id: int,
        current_user: User,
    ) -> dict:
        if current_user.role not in _INSTRUCTOR_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instructor access required")

        _require_cohort(db, cohort_id, current_user.tenant_id)

        assignment = db.query(CohortLearningAssignment).filter(
            CohortLearningAssignment.id == assignment_id,
            CohortLearningAssignment.cohort_id == cohort_id,
        ).first()

        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        db.delete(assignment)
        db.commit()

        return {"success": True}
