from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.models.user_model import User
from app.infrastructure.models.learning_module_model import LearningModule, ModuleSection
from app.infrastructure.models.learning_path_model import LearningPath, PathModule
from app.infrastructure.models.cohort_model import Cohort, CohortEnrollment
from app.infrastructure.models.cohort_learning_assignment_model import CohortLearningAssignment
from app.infrastructure.models.learner_module_progress_model import LearnerModuleProgress
from app.schemas.learning_progress_schema import (
    LearningProgressOverviewResponse,
    CohortProgressResponse,
    CohortSummaryItem,
    OverviewStats,
    TopPathItem,
    StudentProgressItem,
    AssignedPathProgressItem,
    AssignedModuleProgressItem,
)

_INSTRUCTOR_ROLES = {"instructor", "admin"}


class LearningProgressService:

    @staticmethod
    def get_overview(db: Session, current_user: User) -> LearningProgressOverviewResponse:
        if current_user.role not in _INSTRUCTOR_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor access required",
            )

        # All cohorts for this tenant
        cohorts = (
            db.query(Cohort)
            .filter(Cohort.tenant_id == current_user.tenant_id)
            .all()
        )
        cohort_ids = [c.id for c in cohorts]

        # Enrollment counts per cohort
        enrollment_counts: dict[int, int] = {}
        if cohort_ids:
            for row in (
                db.query(
                    CohortEnrollment.cohort_id,
                    func.count(CohortEnrollment.user_id).label("cnt"),
                )
                .filter(CohortEnrollment.cohort_id.in_(cohort_ids))
                .group_by(CohortEnrollment.cohort_id)
                .all()
            ):
                enrollment_counts[row.cohort_id] = int(row.cnt)

        # Assignment counts per cohort
        assignment_stats: dict[int, dict] = {}
        if cohort_ids:
            for row in (
                db.query(
                    CohortLearningAssignment.cohort_id,
                    func.count(CohortLearningAssignment.id).label("total"),
                    func.count(CohortLearningAssignment.learning_path_id).label("paths"),
                    func.count(CohortLearningAssignment.module_id).label("modules"),
                )
                .filter(CohortLearningAssignment.cohort_id.in_(cohort_ids))
                .group_by(CohortLearningAssignment.cohort_id)
                .all()
            ):
                assignment_stats[row.cohort_id] = {
                    "total": int(row.total),
                    "paths": int(row.paths),
                    "modules": int(row.modules),
                }

        cohort_items = [
            CohortSummaryItem(
                id=c.id,
                name=c.name,
                total_students=enrollment_counts.get(c.id, 0),
                total_assignments=assignment_stats.get(c.id, {}).get("total", 0),
                path_assignments=assignment_stats.get(c.id, {}).get("paths", 0),
                module_assignments=assignment_stats.get(c.id, {}).get("modules", 0),
            )
            for c in cohorts
        ]

        # Global progress stats — scoped to all users in this tenant
        tenant_user_ids = [
            row.id
            for row in db.query(User.id).filter(User.tenant_id == current_user.tenant_id).all()
        ]

        total_progress_records = 0
        active_learners = 0
        completed_modules = 0
        active_last_week = 0
        avg_completion_rate = 0.0

        if tenant_user_ids:
            total_progress_records = (
                db.query(func.count(LearnerModuleProgress.id))
                .filter(LearnerModuleProgress.user_id.in_(tenant_user_ids))
                .scalar() or 0
            )

            active_learners = (
                db.query(func.count(func.distinct(LearnerModuleProgress.user_id)))
                .filter(LearnerModuleProgress.user_id.in_(tenant_user_ids))
                .scalar() or 0
            )

            cutoff_week = datetime.utcnow() - timedelta(days=7)
            active_last_week = (
                db.query(func.count(func.distinct(LearnerModuleProgress.user_id)))
                .filter(
                    LearnerModuleProgress.user_id.in_(tenant_user_ids),
                    LearnerModuleProgress.completed_at >= cutoff_week,
                )
                .scalar() or 0
            )

            # Modules with any progress for this tenant
            module_ids_with_progress = [
                row.module_id
                for row in db.query(func.distinct(LearnerModuleProgress.module_id).label("module_id"))
                .filter(LearnerModuleProgress.user_id.in_(tenant_user_ids))
                .all()
            ]

            if module_ids_with_progress:
                # Section counts per module (bulk)
                section_counts: dict[int, int] = {
                    row.module_id: int(row.cnt)
                    for row in db.query(
                        ModuleSection.module_id,
                        func.count(ModuleSection.id).label("cnt"),
                    )
                    .filter(ModuleSection.module_id.in_(module_ids_with_progress))
                    .group_by(ModuleSection.module_id)
                    .all()
                }

                # Per-(user, module) completion counts (bulk)
                completion_rates: list[float] = []
                for row in (
                    db.query(
                        LearnerModuleProgress.user_id,
                        LearnerModuleProgress.module_id,
                        func.count(LearnerModuleProgress.id).label("done"),
                    )
                    .filter(
                        LearnerModuleProgress.module_id.in_(module_ids_with_progress),
                        LearnerModuleProgress.user_id.in_(tenant_user_ids),
                    )
                    .group_by(LearnerModuleProgress.user_id, LearnerModuleProgress.module_id)
                    .all()
                ):
                    total_sects = section_counts.get(row.module_id, 0)
                    if total_sects > 0:
                        rate = row.done / total_sects
                        completion_rates.append(rate)
                        if row.done >= total_sects:
                            completed_modules += 1

                if completion_rates:
                    avg_completion_rate = round(
                        (sum(completion_rates) / len(completion_rates)) * 100, 1
                    )

        stats = OverviewStats(
            active_learners=active_learners,
            completed_modules=completed_modules,
            total_progress_records=total_progress_records,
            avg_completion_rate=avg_completion_rate,
            active_last_week=active_last_week,
        )

        # Top paths by assignment count (across all tenant cohorts)
        top_path_rows = (
            db.query(
                LearningPath,
                func.count(CohortLearningAssignment.id).label("assignment_count"),
            )
            .outerjoin(
                CohortLearningAssignment,
                CohortLearningAssignment.learning_path_id == LearningPath.id,
            )
            .filter(LearningPath.tenant_id == current_user.tenant_id)
            .group_by(LearningPath.id)
            .order_by(func.count(CohortLearningAssignment.id).desc())
            .limit(10)
            .all()
        )

        top_paths = []
        for path, assignment_count in top_path_rows:
            pm_rows = (
                db.query(PathModule.module_id)
                .filter(PathModule.path_id == path.id)
                .all()
            )
            path_module_ids = [r.module_id for r in pm_rows]

            students_started = 0
            completed_instances = 0
            if path_module_ids and tenant_user_ids:
                students_started = (
                    db.query(func.count(func.distinct(LearnerModuleProgress.user_id)))
                    .filter(
                        LearnerModuleProgress.module_id.in_(path_module_ids),
                        LearnerModuleProgress.user_id.in_(tenant_user_ids),
                    )
                    .scalar() or 0
                )
                completed_instances = (
                    db.query(func.count(LearnerModuleProgress.id))
                    .filter(
                        LearnerModuleProgress.module_id.in_(path_module_ids),
                        LearnerModuleProgress.user_id.in_(tenant_user_ids),
                    )
                    .scalar() or 0
                )

            top_paths.append(TopPathItem(
                id=path.id,
                title=path.title,
                slug=path.slug,
                level=path.level,
                assignments=int(assignment_count or 0),
                total_modules=len(path_module_ids),
                completed_module_instances=completed_instances,
                students_started=students_started,
            ))

        return LearningProgressOverviewResponse(
            cohorts=cohort_items,
            stats=stats,
            top_paths=top_paths,
        )

    @staticmethod
    def get_cohort_progress(
        db: Session, cohort_id: int, current_user: User
    ) -> CohortProgressResponse:
        if current_user.role not in _INSTRUCTOR_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor access required",
            )

        cohort = db.query(Cohort).filter(
            Cohort.id == cohort_id,
            Cohort.tenant_id == current_user.tenant_id,
        ).first()
        if not cohort:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

        # Enrolled users
        enrolled_ids = [
            row.user_id
            for row in db.query(CohortEnrollment.user_id)
            .filter(CohortEnrollment.cohort_id == cohort_id)
            .all()
        ]
        enrolled_users = (
            db.query(User).filter(User.id.in_(enrolled_ids)).all()
            if enrolled_ids else []
        )

        # All learning assignments for the cohort
        assignments = (
            db.query(CohortLearningAssignment)
            .filter(CohortLearningAssignment.cohort_id == cohort_id)
            .all()
        )
        path_assignments = [a for a in assignments if a.learning_path_id is not None]
        module_assignments = [a for a in assignments if a.module_id is not None]

        # Resolve path → module IDs
        assigned_path_ids = [a.learning_path_id for a in path_assignments]
        path_module_map: dict[int, list[int]] = {}  # path_id -> [module_id]
        if assigned_path_ids:
            for row in (
                db.query(PathModule.path_id, PathModule.module_id)
                .filter(PathModule.path_id.in_(assigned_path_ids))
                .all()
            ):
                path_module_map.setdefault(row.path_id, []).append(row.module_id)

        all_path_module_ids = [mid for mids in path_module_map.values() for mid in mids]
        direct_module_ids = [a.module_id for a in module_assignments]
        all_relevant_module_ids = list(set(all_path_module_ids + direct_module_ids))

        # Section counts per module (bulk)
        section_counts: dict[int, int] = {}
        if all_relevant_module_ids:
            for row in (
                db.query(
                    ModuleSection.module_id,
                    func.count(ModuleSection.id).label("cnt"),
                )
                .filter(ModuleSection.module_id.in_(all_relevant_module_ids))
                .group_by(ModuleSection.module_id)
                .all()
            ):
                section_counts[row.module_id] = int(row.cnt)

        # Progress records for enrolled students across relevant modules (bulk)
        # progress_map: (user_id, module_id) -> (done, last_activity)
        progress_map: dict[tuple[int, int], tuple[int, Optional[datetime]]] = {}
        if enrolled_ids and all_relevant_module_ids:
            for row in (
                db.query(
                    LearnerModuleProgress.user_id,
                    LearnerModuleProgress.module_id,
                    func.count(LearnerModuleProgress.id).label("done"),
                    func.max(LearnerModuleProgress.completed_at).label("last_activity"),
                )
                .filter(
                    LearnerModuleProgress.user_id.in_(enrolled_ids),
                    LearnerModuleProgress.module_id.in_(all_relevant_module_ids),
                )
                .group_by(LearnerModuleProgress.user_id, LearnerModuleProgress.module_id)
                .all()
            ):
                progress_map[(row.user_id, row.module_id)] = (int(row.done), row.last_activity)

        # ── Per-student progress ────────────────────────────────────────────
        student_items: list[StudentProgressItem] = []
        for user in enrolled_users:
            modules_started = 0
            modules_completed = 0
            rate_sum = 0.0
            rate_count = 0
            last_activity: Optional[datetime] = None

            for mid in all_relevant_module_ids:
                key = (user.id, mid)
                if key in progress_map:
                    done, act = progress_map[key]
                    total_sects = section_counts.get(mid, 0)
                    modules_started += 1
                    if total_sects > 0:
                        rate_sum += done / total_sects
                        rate_count += 1
                        if done >= total_sects:
                            modules_completed += 1
                    if act and (last_activity is None or act > last_activity):
                        last_activity = act

            avg_progress = round((rate_sum / rate_count) * 100, 1) if rate_count > 0 else 0.0
            student_items.append(StudentProgressItem(
                id=user.id,
                display_name=user.username,
                modules_started=modules_started,
                modules_completed=modules_completed,
                avg_progress=avg_progress,
                last_activity=last_activity.isoformat() if last_activity else None,
            ))

        student_items.sort(key=lambda s: s.avg_progress, reverse=True)

        # ── Per-assigned-path stats ─────────────────────────────────────────
        assigned_path_items: list[AssignedPathProgressItem] = []
        for assignment in path_assignments:
            path = assignment.learning_path
            if not path:
                continue
            this_module_ids = path_module_map.get(path.id, [])

            students_started = 0
            completed_instances = 0
            for uid in enrolled_ids:
                if any((uid, mid) in progress_map for mid in this_module_ids):
                    students_started += 1
                for mid in this_module_ids:
                    key = (uid, mid)
                    if key in progress_map:
                        done, _ = progress_map[key]
                        total_sects = section_counts.get(mid, 0)
                        if total_sects > 0 and done >= total_sects:
                            completed_instances += 1

            assigned_path_items.append(AssignedPathProgressItem(
                assignment_id=assignment.id,
                id=path.id,
                title=path.title,
                slug=path.slug,
                level=path.level,
                total_modules=len(this_module_ids),
                total_students=len(enrolled_ids),
                students_started=students_started,
                completed_instances=completed_instances,
                is_required=assignment.is_required,
                due_date=str(assignment.due_date) if assignment.due_date else None,
            ))

        # ── Per-assigned-module stats ───────────────────────────────────────
        assigned_module_items: list[AssignedModuleProgressItem] = []
        for assignment in module_assignments:
            module = assignment.module
            if not module:
                continue
            total_sects = section_counts.get(module.id, 0)

            students_started = 0
            students_completed = 0
            completion_sum = 0.0
            for uid in enrolled_ids:
                key = (uid, module.id)
                if key in progress_map:
                    done, _ = progress_map[key]
                    students_started += 1
                    if total_sects > 0:
                        completion_sum += done / total_sects
                        if done >= total_sects:
                            students_completed += 1

            avg_completion = (
                round((completion_sum / len(enrolled_ids)) * 100, 1)
                if enrolled_ids else 0.0
            )
            assigned_module_items.append(AssignedModuleProgressItem(
                assignment_id=assignment.id,
                id=module.id,
                title=module.title,
                slug=module.slug,
                level=module.level,
                total_students=len(enrolled_ids),
                students_started=students_started,
                students_completed=students_completed,
                avg_completion=avg_completion,
                is_required=assignment.is_required,
                due_date=str(assignment.due_date) if assignment.due_date else None,
            ))

        return CohortProgressResponse(
            cohort={"id": cohort.id, "name": cohort.name},
            students=student_items,
            assigned_paths=assigned_path_items,
            assigned_modules=assigned_module_items,
        )
