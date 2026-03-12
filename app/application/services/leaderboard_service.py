from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission

from app.schemas.leaderboard_schema import (
    LeaderboardEntry,
    GlobalLeaderboardResponse,
    CohortLeaderboardResponse,
    CohortsResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _timeframe_cutoff(timeframe: str) -> Optional[datetime]:
    if timeframe == "week":
        return datetime.utcnow() - timedelta(days=7)
    if timeframe == "month":
        return datetime.utcnow() - timedelta(days=30)
    return None  # all-time


def _build_streak_map(db: Session, tenant_id: int) -> dict[int, int]:
    """
    Returns {user_id: streak_days} — distinct days in last 7 days
    with at least one passing submission (score_awarded > 0).
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    rows = (
        db.query(
            Submission.user_id,
            func.count(func.distinct(func.date(Submission.created_at))).label("streak"),
        )
        .filter(
            Submission.tenant_id == tenant_id,
            Submission.score_awarded > 0,
            Submission.created_at >= cutoff,
        )
        .group_by(Submission.user_id)
        .all()
    )
    return {row.user_id: int(row.streak) for row in rows}


def _build_entries(rows, streak_map: dict, rank_offset: int = 0) -> list[LeaderboardEntry]:
    entries = []
    for i, row in enumerate(rows):
        avg = float(row.avg_score) if row.avg_score is not None else None
        last_sub = row.last_submission.isoformat() if row.last_submission else None
        entries.append(
            LeaderboardEntry(
                id=str(row.user_id),
                username=row.username,
                rank=rank_offset + i + 1,
                total_points=float(row.total_points or 0),
                challenges_completed=int(row.challenges_completed or 0),
                challenges_attempted=int(row.challenges_attempted or 0),
                avg_score=round(avg, 2) if avg is not None else None,
                current_streak=streak_map.get(row.user_id, 0),
                last_submission=last_sub,
                total_submissions=int(row.total_submissions or 0),
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LeaderboardService:

    @staticmethod
    def get_global(
        db: Session,
        current_user: User,
        timeframe: str = "all-time",
        limit: int = 50,
    ) -> GlobalLeaderboardResponse:
        tenant_id = current_user.tenant_id
        cutoff = _timeframe_cutoff(timeframe)

        sub_q = db.query(
            Submission.user_id,
            func.coalesce(func.sum(Submission.score_awarded), 0).label("total_points"),
            func.count(
                func.distinct(Submission.challenge_version_id)
            ).filter(Submission.score_awarded > 0).label("challenges_completed"),
            func.count(
                func.distinct(Submission.challenge_version_id)
            ).label("challenges_attempted"),
            func.avg(Submission.score_awarded).filter(
                Submission.score_awarded > 0
            ).label("avg_score"),
            func.max(Submission.created_at).label("last_submission"),
            func.count(Submission.id).label("total_submissions"),
        ).filter(Submission.tenant_id == tenant_id)

        if cutoff:
            sub_q = sub_q.filter(Submission.created_at >= cutoff)

        sub_q = sub_q.group_by(Submission.user_id).subquery()

        rows = (
            db.query(
                User.id.label("user_id"),
                User.username,
                sub_q.c.total_points,
                sub_q.c.challenges_completed,
                sub_q.c.challenges_attempted,
                sub_q.c.avg_score,
                sub_q.c.last_submission,
                sub_q.c.total_submissions,
            )
            .join(sub_q, sub_q.c.user_id == User.id)
            .filter(User.tenant_id == tenant_id, sub_q.c.total_points > 0)
            .order_by(
                sub_q.c.total_points.desc(),
                sub_q.c.challenges_completed.desc(),
            )
            .limit(limit)
            .all()
        )

        streak_map = _build_streak_map(db, tenant_id)
        entries = _build_entries(rows, streak_map)

        # Total users in tenant
        total_users = (
            db.query(func.count(User.id))
            .filter(User.tenant_id == tenant_id)
            .scalar() or 0
        )

        # Current user rank: count users with more points than the current user
        user_points = (
            db.query(func.coalesce(func.sum(Submission.score_awarded), 0))
            .filter(
                Submission.user_id == current_user.id,
                Submission.tenant_id == tenant_id,
            )
            .scalar() or 0
        )
        users_above = (
            db.query(func.count(func.distinct(Submission.user_id)))
            .filter(
                Submission.tenant_id == tenant_id,
                Submission.score_awarded > 0,
            )
            .group_by(Submission.user_id)
            .having(func.sum(Submission.score_awarded) > user_points)
            .count()
        )
        current_user_rank = users_above + 1 if user_points > 0 else None

        return GlobalLeaderboardResponse(
            leaderboard=entries,
            totalUsers=total_users,
            currentUserRank=current_user_rank,
            timeframe=timeframe,
        )

    @staticmethod
    def get_cohort(
        db: Session,
        current_user: User,
        cohort_id: int,
        limit: int = 50,
    ) -> CohortLeaderboardResponse:
        # Cohort model not yet implemented — return empty
        return CohortLeaderboardResponse(
            leaderboard=[],
            cohort=None,
            totalUsers=0,
            currentUserRank=None,
        )

    @staticmethod
    def get_cohorts(db: Session, current_user: User) -> CohortsResponse:
        # Cohort model not yet implemented — return empty
        return CohortsResponse(cohorts=[])
