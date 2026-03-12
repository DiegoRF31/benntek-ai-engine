from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, case
from fastapi import HTTPException, status

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.cohort_model import Cohort, CohortEnrollment, CohortChallenge
from app.schemas.analytics_schema import (
    InstructorCohortScoresResponse,
    ScoreDistributionItem,
    CohortProgressItem,
    StudentPerformanceItem,
    CategoryBreakdownItem,
    StrugglingStudentItem,
)

_PASS_THRESHOLD = 70.0
_STRUGGLE_THRESHOLD = 70.0
_BUCKETS = ["0-59", "60-69", "70-79", "80-89", "90-100"]
_INSTRUCTOR_ROLES = {"instructor", "admin"}


def _fmt_dt(d) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.isoformat()


class InstructorAnalyticsService:

    @staticmethod
    def get_cohort_scores(
        db: Session,
        cohort_id: int,
        current_user: User,
    ) -> InstructorCohortScoresResponse:
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

        # ── Scope resolution ─────────────────────────────────────────────
        enrolled_ids: list[int] = [
            row.user_id
            for row in db.query(CohortEnrollment.user_id)
            .filter(CohortEnrollment.cohort_id == cohort_id)
            .all()
        ]

        version_ids: list[int] = [
            row.id
            for row in (
                db.query(ChallengeVersion.id)
                .join(CohortChallenge, CohortChallenge.challenge_id == ChallengeVersion.challenge_id)
                .filter(CohortChallenge.cohort_id == cohort_id)
                .all()
            )
        ]

        enrolled_users = (
            db.query(User).filter(User.id.in_(enrolled_ids)).all()
            if enrolled_ids else []
        )

        # Empty cohort — return skeleton with students flagged as struggling
        if not enrolled_ids or not version_ids:
            return InstructorCohortScoresResponse(
                scoreDistribution=[ScoreDistributionItem(score_range=b, count=0) for b in _BUCKETS],
                cohortProgress=[],
                studentPerformance=[],
                categoryBreakdown=[],
                strugglingStudents=[
                    StrugglingStudentItem(
                        id=u.id,
                        full_name=u.username,
                        email=u.email,
                        avg_score=None,
                        last_activity=None,
                    )
                    for u in enrolled_users
                ],
            )

        # ── Score distribution ────────────────────────────────────────────
        bucket_expr = case(
            (Submission.score_awarded < 60, "0-59"),
            (Submission.score_awarded < 70, "60-69"),
            (Submission.score_awarded < 80, "70-79"),
            (Submission.score_awarded < 90, "80-89"),
            else_="90-100",
        )
        dist_rows = (
            db.query(
                bucket_expr.label("score_range"),
                func.count(Submission.id).label("count"),
            )
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded.isnot(None),
            )
            .group_by(bucket_expr)
            .all()
        )
        dist_map = {row.score_range: int(row.count) for row in dist_rows}
        score_distribution = [
            ScoreDistributionItem(score_range=b, count=dist_map.get(b, 0))
            for b in _BUCKETS
        ]

        # ── Cohort progress (last 30 days) ────────────────────────────────
        cutoff_30 = datetime.utcnow() - timedelta(days=30)
        progress_rows = (
            db.query(
                func.date(Submission.created_at).label("date"),
                func.avg(Submission.score_awarded).label("avg_score"),
                func.max(Submission.score_awarded).label("max_score"),
                func.count(Submission.id).label("submission_count"),
            )
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.created_at >= cutoff_30,
            )
            .group_by(func.date(Submission.created_at))
            .order_by(func.date(Submission.created_at))
            .all()
        )
        cohort_progress = [
            CohortProgressItem(
                date=str(row.date),
                avg_score=round(float(row.avg_score or 0), 2),
                max_score=round(float(row.max_score or 0), 2),
                submission_count=int(row.submission_count),
            )
            for row in progress_rows
        ]

        # ── Per-student submission stats ──────────────────────────────────
        sub_stats_rows = (
            db.query(
                Submission.user_id,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(Submission.id).label("total_submissions"),
                func.max(Submission.created_at).label("last_activity"),
            )
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Submission.user_id)
            .all()
        )
        sub_stats = {row.user_id: row for row in sub_stats_rows}

        # Distinct challenges attempted per student
        attempted_rows = (
            db.query(
                Submission.user_id,
                func.count(func.distinct(ChallengeVersion.challenge_id)).label("attempted"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Submission.user_id)
            .all()
        )
        attempted_by_user = {row.user_id: int(row.attempted) for row in attempted_rows}

        # Challenges passed: distinct challenge_ids where best score >= threshold
        best_sub = (
            db.query(
                Submission.user_id,
                ChallengeVersion.challenge_id,
                func.max(Submission.score_awarded).label("best_score"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Submission.user_id, ChallengeVersion.challenge_id)
            .subquery()
        )
        passed_rows = (
            db.query(
                best_sub.c.user_id,
                func.count(best_sub.c.challenge_id).label("passed"),
            )
            .filter(best_sub.c.best_score >= _PASS_THRESHOLD)
            .group_by(best_sub.c.user_id)
            .all()
        )
        passed_by_user = {row.user_id: int(row.passed) for row in passed_rows}

        # Assemble student performance list (only students with submissions), sorted desc
        student_performance = sorted(
            [
                StudentPerformanceItem(
                    id=u.id,
                    full_name=u.username,
                    email=u.email,
                    avg_score=round(float(sub_stats[u.id].avg_score or 0), 2),
                    challenges_attempted=attempted_by_user.get(u.id, 0),
                    challenges_passed=passed_by_user.get(u.id, 0),
                    total_submissions=int(sub_stats[u.id].total_submissions or 0),
                )
                for u in enrolled_users
                if u.id in sub_stats
            ],
            key=lambda s: s.avg_score,
            reverse=True,
        )

        # Struggling: avg_score < threshold OR no submissions at all
        struggling_students = [
            StrugglingStudentItem(
                id=u.id,
                full_name=u.username,
                email=u.email,
                avg_score=(
                    round(float(sub_stats[u.id].avg_score or 0), 2)
                    if u.id in sub_stats else None
                ),
                last_activity=(
                    _fmt_dt(sub_stats[u.id].last_activity)
                    if u.id in sub_stats else None
                ),
            )
            for u in enrolled_users
            if (
                u.id not in sub_stats
                or float(sub_stats[u.id].avg_score or 0) < _STRUGGLE_THRESHOLD
            )
        ]

        # ── Category breakdown ────────────────────────────────────────────
        cat_rows = (
            db.query(
                Challenge.category,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(func.distinct(Submission.user_id)).label("students_attempted"),
                func.count(Submission.id).label("total_submissions"),
                func.count(func.distinct(Challenge.id)).label("unique_challenges"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
            )
            .group_by(Challenge.category)
            .all()
        )
        cat_passed_rows = (
            db.query(
                Challenge.category,
                func.count(Submission.id).label("passed_count"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id.in_(enrolled_ids),
                Submission.challenge_version_id.in_(version_ids),
                Submission.score_awarded >= _PASS_THRESHOLD,
            )
            .group_by(Challenge.category)
            .all()
        )
        cat_passed_map = {row.category: int(row.passed_count) for row in cat_passed_rows}
        category_breakdown = [
            CategoryBreakdownItem(
                category=row.category,
                avg_score=round(float(row.avg_score or 0), 2),
                students_attempted=int(row.students_attempted or 0),
                total_submissions=int(row.total_submissions or 0),
                passed_count=cat_passed_map.get(row.category, 0),
                unique_challenges=int(row.unique_challenges or 0),
            )
            for row in cat_rows
        ]

        return InstructorCohortScoresResponse(
            scoreDistribution=score_distribution,
            cohortProgress=cohort_progress,
            studentPerformance=student_performance,
            categoryBreakdown=category_breakdown,
            strugglingStudents=struggling_students,
        )
