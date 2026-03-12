from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.cohort_model import Cohort, CohortEnrollment, CohortChallenge

from app.schemas.cohort_schema import (
    CohortItem,
    InstructorInfo,
    CohortsResponse,
    CohortCreateResponse,
    StudentItem,
    ChallengeAssignmentItem,
    CohortDetailResponse,
    AvailableChallengeItem,
    AvailableChallengesResponse,
    AvailableStudentItem,
    AvailableStudentsResponse,
    CategoryPerformanceItem,
    EngagementTrendItem,
    DifficultyStatItem,
    TopStudentItem,
    ChallengeAttentionItem,
    Recommendation,
    InstructorAnalyticsResponse,
)

_DIFFICULTY_MAP = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert"}
_DIFFICULTY_ORDER = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}


def _fmt_date(d) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.isoformat()


def _build_cohort_item(cohort: Cohort, student_count: int, challenge_count: int) -> CohortItem:
    return CohortItem(
        id=cohort.id,
        name=cohort.name,
        description=cohort.description,
        start_date=_fmt_date(cohort.start_date),
        end_date=_fmt_date(cohort.end_date),
        is_active=bool(cohort.is_active),
        student_count=int(student_count),
        challenge_count=int(challenge_count),
        created_at=cohort.created_at.isoformat() if cohort.created_at else "",
    )


class CohortService:

    # ── List cohorts ───────────────────────────────────────────────────────

    @staticmethod
    def get_cohorts(db: Session, current_user: User) -> CohortsResponse:
        enrollment_counts = (
            db.query(
                CohortEnrollment.cohort_id,
                func.count(CohortEnrollment.id).label("cnt"),
            )
            .group_by(CohortEnrollment.cohort_id)
            .subquery()
        )
        challenge_counts = (
            db.query(
                CohortChallenge.cohort_id,
                func.count(CohortChallenge.id).label("cnt"),
            )
            .group_by(CohortChallenge.cohort_id)
            .subquery()
        )

        rows = (
            db.query(
                Cohort,
                func.coalesce(enrollment_counts.c.cnt, 0).label("student_count"),
                func.coalesce(challenge_counts.c.cnt, 0).label("challenge_count"),
            )
            .outerjoin(enrollment_counts, enrollment_counts.c.cohort_id == Cohort.id)
            .outerjoin(challenge_counts, challenge_counts.c.cohort_id == Cohort.id)
            .filter(
                Cohort.tenant_id == current_user.tenant_id,
                Cohort.instructor_id == current_user.id,
            )
            .order_by(Cohort.created_at.desc())
            .all()
        )

        cohorts = [_build_cohort_item(c, sc, cc) for c, sc, cc in rows]

        return CohortsResponse(
            cohorts=cohorts,
            instructor=InstructorInfo(
                id=current_user.id,
                name=current_user.username,
                email=current_user.email,
                role=current_user.role,
            ),
        )

    # ── Create cohort ──────────────────────────────────────────────────────

    @staticmethod
    def create_cohort(
        db: Session,
        current_user: User,
        name: str,
        description: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> CohortCreateResponse:
        cohort = Cohort(
            tenant_id=current_user.tenant_id,
            instructor_id=current_user.id,
            name=name,
            description=description or None,
            start_date=start_date or None,
            end_date=end_date or None,
            is_active=True,
        )
        db.add(cohort)
        db.commit()
        db.refresh(cohort)
        return CohortCreateResponse(success=True, cohort_id=cohort.id)

    # ── Cohort detail ──────────────────────────────────────────────────────

    @staticmethod
    def get_cohort_detail(db: Session, current_user: User, cohort_id: int) -> CohortDetailResponse:
        from fastapi import HTTPException

        cohort = (
            db.query(Cohort)
            .filter(Cohort.id == cohort_id, Cohort.tenant_id == current_user.tenant_id)
            .first()
        )
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        if cohort.instructor_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # Enrollment counts for the header card
        student_count = (
            db.query(func.count(CohortEnrollment.id))
            .filter(CohortEnrollment.cohort_id == cohort_id)
            .scalar() or 0
        )
        challenge_count = (
            db.query(func.count(CohortChallenge.id))
            .filter(CohortChallenge.cohort_id == cohort_id)
            .scalar() or 0
        )
        cohort_item = _build_cohort_item(cohort, student_count, challenge_count)

        # Students with submission stats
        sub_stats = (
            db.query(
                Submission.user_id,
                func.count(func.distinct(Submission.challenge_version_id)).filter(
                    Submission.score_awarded > 0
                ).label("challenges_completed"),
                func.coalesce(func.sum(Submission.score_awarded), 0).label("total_points"),
                func.avg(Submission.score_awarded).label("avg_score"),
            )
            .join(User, User.id == Submission.user_id)
            .filter(User.tenant_id == current_user.tenant_id)
            .group_by(Submission.user_id)
            .subquery()
        )

        student_rows = (
            db.query(
                User,
                CohortEnrollment.enrolled_at,
                func.coalesce(sub_stats.c.challenges_completed, 0).label("challenges_completed"),
                func.coalesce(sub_stats.c.total_points, 0).label("total_points"),
                sub_stats.c.avg_score,
            )
            .join(CohortEnrollment, CohortEnrollment.user_id == User.id)
            .outerjoin(sub_stats, sub_stats.c.user_id == User.id)
            .filter(CohortEnrollment.cohort_id == cohort_id)
            .order_by(func.coalesce(sub_stats.c.total_points, 0).desc())
            .all()
        )

        students = [
            StudentItem(
                id=u.id,
                full_name=u.username,
                email=u.email,
                enrolled_at=enrolled_at.isoformat() if enrolled_at else "",
                challenges_completed=int(challenges_completed),
                total_points=float(total_points or 0),
                avg_score=round(float(avg_score or 0), 2),
            )
            for u, enrolled_at, challenges_completed, total_points, avg_score in student_rows
        ]

        # Assigned challenges with attempt stats (scoped to enrolled students)
        enrolled_user_ids = [s.id for s, *_ in student_rows]

        challenge_rows = (
            db.query(
                Challenge,
                CohortChallenge.due_date,
                CohortChallenge.assigned_at,
            )
            .join(CohortChallenge, CohortChallenge.challenge_id == Challenge.id)
            .filter(CohortChallenge.cohort_id == cohort_id)
            .order_by(CohortChallenge.assigned_at.desc())
            .all()
        )

        challenges = []
        for challenge, due_date, assigned_at in challenge_rows:
            # Attempt stats from enrolled students
            attempts = 0
            passed = 0
            if enrolled_user_ids:
                version_ids = [
                    v.id for v in db.query(ChallengeVersion.id)
                    .filter(ChallengeVersion.challenge_id == challenge.id)
                    .all()
                ]
                if version_ids:
                    attempts = (
                        db.query(func.count(func.distinct(Submission.user_id)))
                        .filter(
                            Submission.challenge_version_id.in_(version_ids),
                            Submission.user_id.in_(enrolled_user_ids),
                        )
                        .scalar() or 0
                    )
                    passed = (
                        db.query(func.count(func.distinct(Submission.user_id)))
                        .filter(
                            Submission.challenge_version_id.in_(version_ids),
                            Submission.user_id.in_(enrolled_user_ids),
                            Submission.score_awarded > 0,
                        )
                        .scalar() or 0
                    )

            challenges.append(
                ChallengeAssignmentItem(
                    id=challenge.id,
                    title=challenge.title,
                    difficulty=_DIFFICULTY_MAP.get(challenge.difficulty, "beginner"),
                    category=challenge.category,
                    due_date=_fmt_date(due_date),
                    assigned_at=assigned_at.isoformat() if assigned_at else "",
                    students_attempted=int(attempts),
                    students_completed=int(passed),
                )
            )

        return CohortDetailResponse(cohort=cohort_item, students=students, challenges=challenges)

    # ── Assign challenge ───────────────────────────────────────────────────

    @staticmethod
    def assign_challenge(
        db: Session,
        current_user: User,
        cohort_id: int,
        challenge_id: int,
        due_date: Optional[str],
    ) -> dict:
        from fastapi import HTTPException

        cohort = (
            db.query(Cohort)
            .filter(Cohort.id == cohort_id, Cohort.tenant_id == current_user.tenant_id)
            .first()
        )
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        if cohort.instructor_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        existing = (
            db.query(CohortChallenge)
            .filter(CohortChallenge.cohort_id == cohort_id, CohortChallenge.challenge_id == challenge_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Challenge already assigned to this cohort")

        db.add(CohortChallenge(cohort_id=cohort_id, challenge_id=challenge_id, due_date=due_date or None))
        db.commit()
        return {"success": True}

    # ── Enroll student ─────────────────────────────────────────────────────

    @staticmethod
    def enroll_student(
        db: Session,
        current_user: User,
        cohort_id: int,
        student_id: int,
    ) -> dict:
        from fastapi import HTTPException

        cohort = (
            db.query(Cohort)
            .filter(Cohort.id == cohort_id, Cohort.tenant_id == current_user.tenant_id)
            .first()
        )
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        if cohort.instructor_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        existing = (
            db.query(CohortEnrollment)
            .filter(CohortEnrollment.cohort_id == cohort_id, CohortEnrollment.user_id == student_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Student already enrolled in this cohort")

        db.add(CohortEnrollment(cohort_id=cohort_id, user_id=student_id))
        db.commit()
        return {"success": True}

    # ── Available challenges ────────────────────────────────────────────────

    @staticmethod
    def get_available_challenges(
        db: Session, current_user: User, cohort_id: int
    ) -> AvailableChallengesResponse:
        assigned_ids = [
            row.challenge_id
            for row in db.query(CohortChallenge.challenge_id)
            .filter(CohortChallenge.cohort_id == cohort_id)
            .all()
        ]

        query = db.query(Challenge).filter(Challenge.is_active == True)
        if assigned_ids:
            query = query.filter(Challenge.id.notin_(assigned_ids))

        rows = query.order_by(Challenge.category, Challenge.difficulty, Challenge.title).all()

        return AvailableChallengesResponse(
            challenges=[
                AvailableChallengeItem(
                    id=c.id,
                    title=c.title,
                    difficulty=_DIFFICULTY_MAP.get(c.difficulty, "beginner"),
                    category=c.category,
                )
                for c in rows
            ]
        )

    # ── Available students ──────────────────────────────────────────────────

    @staticmethod
    def get_available_students(
        db: Session, current_user: User, cohort_id: int
    ) -> AvailableStudentsResponse:
        enrolled_ids = [
            row.user_id
            for row in db.query(CohortEnrollment.user_id)
            .filter(CohortEnrollment.cohort_id == cohort_id)
            .all()
        ]

        query = (
            db.query(User)
            .filter(
                User.tenant_id == current_user.tenant_id,
                User.role == "user",
                User.is_active == True,
            )
        )
        if enrolled_ids:
            query = query.filter(User.id.notin_(enrolled_ids))

        rows = query.order_by(User.username).all()

        return AvailableStudentsResponse(
            students=[
                AvailableStudentItem(id=u.id, full_name=u.username, email=u.email)
                for u in rows
            ]
        )

    # ── Instructor analytics ────────────────────────────────────────────────

    @staticmethod
    def get_analytics(db: Session, current_user: User) -> InstructorAnalyticsResponse:
        tenant_id = current_user.tenant_id
        instructor_id = current_user.id
        now = datetime.utcnow()
        cutoff_30 = now - timedelta(days=30)

        # IDs of cohorts managed by this instructor
        cohort_ids = [
            row.id
            for row in db.query(Cohort.id)
            .filter(Cohort.instructor_id == instructor_id, Cohort.tenant_id == tenant_id)
            .all()
        ]

        # IDs of users enrolled in those cohorts
        enrolled_user_ids = []
        if cohort_ids:
            enrolled_user_ids = [
                row.user_id
                for row in db.query(CohortEnrollment.user_id)
                .filter(CohortEnrollment.cohort_id.in_(cohort_ids))
                .distinct()
                .all()
            ]

        # ── Category performance ─────────────────────────────────────────
        category_perf: list[CategoryPerformanceItem] = []
        if enrolled_user_ids:
            cat_rows = (
                db.query(
                    Challenge.category,
                    func.count(Submission.id).label("total_submissions"),
                    func.count(Submission.id).filter(Submission.score_awarded > 0).label("successful_submissions"),
                    func.avg(Submission.score_awarded).label("avg_score"),
                    func.count(func.distinct(Submission.user_id)).label("unique_students"),
                )
                .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
                .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
                .filter(Submission.user_id.in_(enrolled_user_ids))
                .group_by(Challenge.category)
                .order_by(func.avg(Submission.score_awarded).desc())
                .all()
            )
            category_perf = [
                CategoryPerformanceItem(
                    category=row.category,
                    total_submissions=int(row.total_submissions),
                    successful_submissions=int(row.successful_submissions),
                    avg_score=round(float(row.avg_score or 0), 1),
                    unique_students=int(row.unique_students),
                )
                for row in cat_rows
            ]

        # ── Engagement trend (last 30 days) ──────────────────────────────
        engagement_trend: list[EngagementTrendItem] = []
        if enrolled_user_ids:
            eng_rows = (
                db.query(
                    func.date(Submission.created_at).label("date"),
                    func.count(func.distinct(Submission.user_id)).label("active_students"),
                    func.count(Submission.id).label("total_attempts"),
                    func.count(Submission.id).filter(Submission.score_awarded > 0).label("successful_attempts"),
                )
                .filter(
                    Submission.user_id.in_(enrolled_user_ids),
                    Submission.created_at >= cutoff_30,
                )
                .group_by(func.date(Submission.created_at))
                .order_by(func.date(Submission.created_at))
                .all()
            )
            engagement_trend = [
                EngagementTrendItem(
                    date=str(row.date),
                    active_students=int(row.active_students),
                    total_attempts=int(row.total_attempts),
                    successful_attempts=int(row.successful_attempts),
                )
                for row in eng_rows
            ]

        # ── Difficulty stats ─────────────────────────────────────────────
        # Assigned challenges across instructor's cohorts
        difficulty_stats: list[DifficultyStatItem] = []
        if cohort_ids:
            assigned_challenge_ids = [
                row.challenge_id
                for row in db.query(CohortChallenge.challenge_id)
                .filter(CohortChallenge.cohort_id.in_(cohort_ids))
                .distinct()
                .all()
            ]
            if assigned_challenge_ids:
                diff_rows = (
                    db.query(
                        Challenge.difficulty,
                        func.count(func.distinct(Challenge.id)).label("assigned_challenges"),
                        func.count(Submission.id).label("total_attempts"),
                        func.count(Submission.id).filter(Submission.score_awarded > 0).label("successful_attempts"),
                        func.avg(Submission.score_awarded).label("avg_score"),
                    )
                    .outerjoin(ChallengeVersion, ChallengeVersion.challenge_id == Challenge.id)
                    .outerjoin(
                        Submission,
                        (Submission.challenge_version_id == ChallengeVersion.id)
                        & (Submission.user_id.in_(enrolled_user_ids) if enrolled_user_ids else False),
                    )
                    .filter(Challenge.id.in_(assigned_challenge_ids))
                    .group_by(Challenge.difficulty)
                    .all()
                )
                difficulty_stats = sorted(
                    [
                        DifficultyStatItem(
                            difficulty=_DIFFICULTY_MAP.get(row.difficulty, "beginner"),
                            assigned_challenges=int(row.assigned_challenges),
                            total_attempts=int(row.total_attempts or 0),
                            successful_attempts=int(row.successful_attempts or 0),
                            avg_score=round(float(row.avg_score or 0), 1),
                        )
                        for row in diff_rows
                    ],
                    key=lambda d: _DIFFICULTY_ORDER.get(d.difficulty, 0),
                )

        # ── Top students ─────────────────────────────────────────────────
        top_students: list[TopStudentItem] = []
        if enrolled_user_ids:
            top_rows = (
                db.query(
                    User.username,
                    func.count(func.distinct(Submission.challenge_version_id)).filter(
                        Submission.score_awarded > 0
                    ).label("challenges_completed"),
                    func.coalesce(func.sum(Submission.score_awarded), 0).label("total_points"),
                    func.avg(Submission.score_awarded).label("avg_score"),
                )
                .outerjoin(Submission, Submission.user_id == User.id)
                .filter(User.id.in_(enrolled_user_ids))
                .group_by(User.id)
                .having(func.count(func.distinct(Submission.challenge_version_id)).filter(Submission.score_awarded > 0) > 0)
                .order_by(func.coalesce(func.sum(Submission.score_awarded), 0).desc())
                .limit(10)
                .all()
            )
            top_students = [
                TopStudentItem(
                    full_name=row.username,
                    challenges_completed=int(row.challenges_completed),
                    total_points=float(row.total_points or 0),
                    avg_score=round(float(row.avg_score or 0), 1),
                )
                for row in top_rows
            ]

        # ── Challenges needing attention (pass rate < 60%) ───────────────
        attention_items: list[ChallengeAttentionItem] = []
        if cohort_ids and enrolled_user_ids:
            for cohort_id in cohort_ids:
                cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
                if not cohort:
                    continue
                cc_rows = (
                    db.query(Challenge, CohortChallenge.due_date)
                    .join(CohortChallenge, CohortChallenge.challenge_id == Challenge.id)
                    .filter(CohortChallenge.cohort_id == cohort_id)
                    .all()
                )
                for challenge, due_date in cc_rows:
                    version_ids = [
                        v.id for v in db.query(ChallengeVersion.id)
                        .filter(ChallengeVersion.challenge_id == challenge.id)
                        .all()
                    ]
                    if not version_ids:
                        continue
                    attempted = (
                        db.query(func.count(func.distinct(Submission.user_id)))
                        .filter(
                            Submission.challenge_version_id.in_(version_ids),
                            Submission.user_id.in_(enrolled_user_ids),
                        )
                        .scalar() or 0
                    )
                    if attempted == 0:
                        continue
                    passed = (
                        db.query(func.count(func.distinct(Submission.user_id)))
                        .filter(
                            Submission.challenge_version_id.in_(version_ids),
                            Submission.user_id.in_(enrolled_user_ids),
                            Submission.score_awarded > 0,
                        )
                        .scalar() or 0
                    )
                    pass_rate = round((passed / attempted) * 100, 1) if attempted else 0
                    if pass_rate < 60:
                        attention_items.append(
                            ChallengeAttentionItem(
                                title=challenge.title,
                                difficulty=_DIFFICULTY_MAP.get(challenge.difficulty, "beginner"),
                                category=challenge.category,
                                cohort_name=cohort.name,
                                due_date=_fmt_date(due_date),
                                students_attempted=int(attempted),
                                students_passed=int(passed),
                                pass_rate=pass_rate,
                            )
                        )

        attention_items.sort(key=lambda x: x.pass_rate)

        # ── Recommendations ───────────────────────────────────────────────
        recommendations: list[Recommendation] = []

        if category_perf:
            lowest = category_perf[-1]
            if lowest.avg_score < 70:
                recommendations.append(
                    Recommendation(
                        type="warning",
                        title="Low Performance Detected",
                        message=f"Students are struggling with {lowest.category} challenges ({lowest.avg_score}% avg). Consider adding more foundational material or hints.",
                        action="Review Challenge Difficulty",
                    )
                )

        if len(engagement_trend) >= 7:
            recent_avg = sum(d.active_students for d in engagement_trend[-3:]) / 3
            older_avg = sum(d.active_students for d in engagement_trend[-6:-3]) / 3
            if older_avg > 0:
                if recent_avg < older_avg * 0.7:
                    recommendations.append(
                        Recommendation(
                            type="alert",
                            title="Engagement Declining",
                            message="Student activity has dropped 30% in the past week. Consider sending a reminder or introducing new content.",
                            action="Boost Engagement",
                        )
                    )
                elif recent_avg > older_avg * 1.3:
                    recommendations.append(
                        Recommendation(
                            type="success",
                            title="Strong Engagement",
                            message="Student activity is up 30%! Students are highly engaged with recent challenges.",
                            action="Keep Momentum",
                        )
                    )

        expert_stat = next((d for d in difficulty_stats if d.difficulty == "expert"), None)
        if not expert_stat or expert_stat.assigned_challenges == 0:
            recommendations.append(
                Recommendation(
                    type="info",
                    title="Advanced Content Opportunity",
                    message="No expert-level challenges assigned yet. Top performers may benefit from more advanced material.",
                    action="Add Expert Challenges",
                )
            )

        return InstructorAnalyticsResponse(
            categoryPerformance=category_perf,
            engagementTrend=engagement_trend,
            difficultyStats=difficulty_stats,
            topStudents=top_students,
            challengesNeedingAttention=attention_items[:5],
            recommendations=recommendations,
        )
