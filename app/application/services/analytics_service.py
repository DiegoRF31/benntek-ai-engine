from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion

from app.schemas.analytics_schema import (
    LearnerAnalyticsResponse,
    ScoreProgressionItem,
    CategoryScore,
    DifficultyScore,
    ImprovementItem,
    WeeklyActivity,
)

_DIFFICULTY_MAP = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert"}
_DIFFICULTY_ORDER = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}


class AnalyticsService:

    @staticmethod
    def get_learner_scores(db: Session, current_user: User) -> LearnerAnalyticsResponse:
        user_id = current_user.id
        tenant_id = current_user.tenant_id
        now = datetime.utcnow()

        # ── Score progression (last 30 days, per day) ────────────────────
        cutoff_30 = now - timedelta(days=30)
        progression_rows = (
            db.query(
                func.date(Submission.created_at).label("date"),
                func.avg(Submission.score_awarded).label("avg_score"),
                func.max(Submission.score_awarded).label("max_score"),
                func.count(Submission.id).label("submission_count"),
            )
            .filter(
                Submission.user_id == user_id,
                Submission.created_at >= cutoff_30,
            )
            .group_by(func.date(Submission.created_at))
            .order_by(func.date(Submission.created_at))
            .all()
        )
        score_progression = [
            ScoreProgressionItem(
                date=str(row.date),
                avg_score=round(float(row.avg_score or 0), 2),
                max_score=round(float(row.max_score or 0), 2),
                submission_count=int(row.submission_count),
            )
            for row in progression_rows
        ]

        # ── Category scores ──────────────────────────────────────────────
        category_rows = (
            db.query(
                Challenge.category,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.min(
                    Submission.score_awarded
                ).filter(Submission.score_awarded > 0).label("min_score"),
                func.max(Submission.score_awarded).label("max_score"),
                func.count(func.distinct(Submission.challenge_version_id)).label("challenges_attempted"),
                func.count(func.distinct(Submission.challenge_version_id)).filter(
                    Submission.score_awarded > 0
                ).label("challenges_passed"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(Submission.user_id == user_id)
            .group_by(Challenge.category)
            .all()
        )
        category_scores = [
            CategoryScore(
                category=row.category,
                avg_score=round(float(row.avg_score or 0), 2),
                min_score=round(float(row.min_score or 0), 2),
                max_score=round(float(row.max_score or 0), 2),
                challenges_attempted=int(row.challenges_attempted or 0),
                challenges_passed=int(row.challenges_passed or 0),
            )
            for row in category_rows
        ]

        # ── Difficulty scores ────────────────────────────────────────────
        difficulty_rows = (
            db.query(
                Challenge.difficulty,
                func.avg(Submission.score_awarded).label("avg_score"),
                func.count(func.distinct(Submission.challenge_version_id)).label("challenges_attempted"),
                func.count(func.distinct(Submission.challenge_version_id)).filter(
                    Submission.score_awarded > 0
                ).label("challenges_passed"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(Submission.user_id == user_id)
            .group_by(Challenge.difficulty)
            .all()
        )
        difficulty_scores = sorted(
            [
                DifficultyScore(
                    difficulty=_DIFFICULTY_MAP.get(row.difficulty, "beginner"),
                    avg_score=round(float(row.avg_score or 0), 2),
                    challenges_attempted=int(row.challenges_attempted or 0),
                    challenges_passed=int(row.challenges_passed or 0),
                )
                for row in difficulty_rows
            ],
            key=lambda d: _DIFFICULTY_ORDER.get(d.difficulty, 0),
        )

        # ── Improvements (best vs first attempt per challenge version) ───
        # Subquery: first score per challenge_version
        first_sub = (
            db.query(
                Submission.challenge_version_id,
                func.min(Submission.score_awarded).label("first_score"),
            )
            .filter(Submission.user_id == user_id)
            .group_by(Submission.challenge_version_id)
            .subquery()
        )
        # Subquery: best score per challenge_version
        best_sub = (
            db.query(
                Submission.challenge_version_id,
                func.max(Submission.score_awarded).label("best_score"),
            )
            .filter(Submission.user_id == user_id)
            .group_by(Submission.challenge_version_id)
            .subquery()
        )
        improvement_rows = (
            db.query(
                Challenge.id,
                Challenge.title,
                Challenge.category,
                first_sub.c.first_score,
                best_sub.c.best_score,
            )
            .join(ChallengeVersion, ChallengeVersion.challenge_id == Challenge.id)
            .join(first_sub, first_sub.c.challenge_version_id == ChallengeVersion.id)
            .join(best_sub, best_sub.c.challenge_version_id == ChallengeVersion.id)
            .filter(best_sub.c.best_score > first_sub.c.first_score)
            .order_by((best_sub.c.best_score - first_sub.c.first_score).desc())
            .limit(10)
            .all()
        )
        improvements = [
            ImprovementItem(
                id=row.id,
                title=row.title,
                category=row.category,
                first_score=round(float(row.first_score or 0), 2),
                best_score=round(float(row.best_score or 0), 2),
                improvement=round(float((row.best_score or 0) - (row.first_score or 0)), 2),
            )
            for row in improvement_rows
        ]

        # ── Percentile ───────────────────────────────────────────────────
        user_total = (
            db.query(func.coalesce(func.sum(Submission.score_awarded), 0))
            .filter(
                Submission.user_id == user_id,
                Submission.score_awarded > 0,
            )
            .scalar() or 0
        )
        # Count tenant users with lower total score
        totals_sub = (
            db.query(
                Submission.user_id,
                func.sum(Submission.score_awarded).label("total"),
            )
            .join(User, User.id == Submission.user_id)
            .filter(
                User.tenant_id == tenant_id,
                Submission.score_awarded > 0,
            )
            .group_by(Submission.user_id)
            .subquery()
        )
        total_users_with_score = (
            db.query(func.count(totals_sub.c.user_id)).scalar() or 1
        )
        users_below = (
            db.query(func.count(totals_sub.c.user_id))
            .filter(totals_sub.c.total < user_total)
            .scalar() or 0
        )
        percentile = round((users_below / total_users_with_score) * 100) if total_users_with_score > 0 else 50

        # ── Weekly activity (last 90 days) ───────────────────────────────
        cutoff_90 = now - timedelta(days=90)
        weekly_rows = (
            db.query(
                func.date_trunc("week", Submission.created_at).label("week_start"),
                func.count(func.distinct(func.date(Submission.created_at))).label("active_days"),
                func.count(Submission.id).label("total_submissions"),
                func.avg(Submission.score_awarded).label("avg_score"),
            )
            .filter(
                Submission.user_id == user_id,
                Submission.created_at >= cutoff_90,
            )
            .group_by(func.date_trunc("week", Submission.created_at))
            .order_by(func.date_trunc("week", Submission.created_at).desc())
            .limit(12)
            .all()
        )
        weekly_activity = [
            WeeklyActivity(
                week=str(row.week_start)[:10] if row.week_start else "",
                active_days=int(row.active_days or 0),
                total_submissions=int(row.total_submissions or 0),
                avg_score=round(float(row.avg_score or 0), 2),
            )
            for row in weekly_rows
        ]

        return LearnerAnalyticsResponse(
            scoreProgression=score_progression,
            categoryScores=category_scores,
            difficultyScores=difficulty_scores,
            improvements=improvements,
            percentile=percentile,
            weeklyActivity=weekly_activity,
        )
