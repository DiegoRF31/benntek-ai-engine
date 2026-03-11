from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.user_skill_progress_model import UserSkillProgress

from app.schemas.dashboard_schema import (
    DashboardResponse,
    UserStats,
    SkillRadarItem,
    ChallengeInfo,
    RecentSubmission,
    LeaderboardEntry,
    LastActiveItem,
    LearningData,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_MAP = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert"}


def _map_difficulty(value: int) -> str:
    return _DIFFICULTY_MAP.get(value, "beginner")


def _compute_max_score(scoring_rules: dict) -> float:
    if not scoring_rules:
        return 0.0
    return float(sum(scoring_rules.values()))


def _skill_to_proficiency(skill_score: float) -> float:
    """Normalize skill_score to a 0–100 scale (500 pts = max level 4 = 100%)."""
    return min(100.0, round((skill_score / 500.0) * 100, 1))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DashboardService:

    @staticmethod
    def get_dashboard(db: Session, current_user: User) -> DashboardResponse:
        user_id = current_user.id
        tenant_id = current_user.tenant_id

        # ── User submissions ─────────────────────────────────────────────
        user_submissions = (
            db.query(Submission)
            .filter(Submission.user_id == user_id)
            .all()
        )

        total_challenges_attempted = len(
            set(s.challenge_version_id for s in user_submissions)
        )
        total_points = sum(s.score_awarded or 0.0 for s in user_submissions)
        solved_versions = set(
            s.challenge_version_id for s in user_submissions if (s.score_awarded or 0) > 0
        )
        total_challenges_solved = len(solved_versions)
        challenges_completed = total_challenges_solved
        average_score = (
            total_points / len(user_submissions) if user_submissions else 0.0
        )

        # ── Total users in tenant ────────────────────────────────────────
        total_users = (
            db.query(func.count(User.id))
            .filter(User.tenant_id == tenant_id)
            .scalar() or 0
        )

        # ── User rank within tenant (by total points) ────────────────────
        tenant_points = (
            db.query(
                User.id,
                func.coalesce(func.sum(Submission.score_awarded), 0).label("pts"),
            )
            .outerjoin(
                Submission,
                (Submission.user_id == User.id) & (Submission.tenant_id == tenant_id),
            )
            .filter(User.tenant_id == tenant_id)
            .group_by(User.id)
            .order_by(func.coalesce(func.sum(Submission.score_awarded), 0).desc())
            .all()
        )
        user_rank = next(
            (i + 1 for i, row in enumerate(tenant_points) if row[0] == user_id),
            total_users,
        )

        # ── Skill radar from UserSkillProgress ───────────────────────────
        skill_records = (
            db.query(UserSkillProgress)
            .filter(UserSkillProgress.user_id == user_id)
            .all()
        )
        skill_radar = [
            SkillRadarItem(
                category=s.skill_name,
                proficiency=_skill_to_proficiency(s.skill_score),
                fullMark=100.0,
            )
            for s in skill_records
        ]

        sorted_skills = sorted(skill_records, key=lambda s: s.skill_score, reverse=True)
        strong_categories = [s.skill_name for s in sorted_skills if s.level >= 3][:3]
        weak_categories   = [s.skill_name for s in sorted_skills if s.level <= 1][:3]

        user_stats = UserStats(
            total_challenges_attempted=total_challenges_attempted,
            total_challenges_solved=total_challenges_solved,
            challenges_completed=challenges_completed,
            total_points=round(total_points, 2),
            average_score=round(average_score, 2),
            current_streak=0,
            rank=user_rank,
            global_rank=user_rank,
            total_users=total_users,
            strong_categories=strong_categories,
            weak_categories=weak_categories,
            skill_radar=skill_radar,
            ai_recommendations=[],
        )

        # ── Recent submissions (last 5, with nested challenge info) ──────
        recent_subs_db = (
            db.query(Submission)
            .filter(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc())
            .limit(5)
            .all()
        )

        recent_submissions = []
        for sub in recent_subs_db:
            version: ChallengeVersion | None = sub.challenge_version
            if not version:
                continue
            challenge: Challenge | None = version.challenge
            if not challenge:
                continue

            max_score = _compute_max_score(version.scoring_rules)
            recent_submissions.append(
                RecentSubmission(
                    id=sub.id,
                    challenge_id=challenge.id,
                    user_id=sub.user_id,
                    attempt_number=sub.attempt_number,
                    score=sub.score_awarded or 0.0,
                    max_score=max_score,
                    status="completed",
                    has_passed=(sub.score_awarded or 0) > 0,
                    submitted_at=sub.created_at.isoformat(),
                    challenge=ChallengeInfo(
                        id=challenge.id,
                        title=challenge.title,
                        description=version.description,
                        difficulty=_map_difficulty(challenge.difficulty),
                        category=challenge.category,
                        challenge_type="prompt_injection",
                        points=max_score,
                        time_limit_minutes=None,
                        is_published=version.is_published,
                    ),
                )
            )

        # ── Last active item ─────────────────────────────────────────────
        last_active_item = None
        if recent_subs_db:
            latest = recent_subs_db[0]
            version = latest.challenge_version
            challenge = version.challenge if version else None
            if challenge:
                max_score = _compute_max_score(version.scoring_rules)
                last_active_item = LastActiveItem(
                    type="challenge",
                    id=challenge.id,
                    title=challenge.title,
                    passed=(latest.score_awarded or 0) > 0,
                    score=latest.score_awarded or 0.0,
                    max_score=max_score,
                    url=f"/challenges/{challenge.id}",
                )

        # ── Leaderboard (top 5 in tenant) ────────────────────────────────
        leaderboard_rows = (
            db.query(
                User.id,
                User.username,
                func.coalesce(func.sum(Submission.score_awarded), 0).label("total_points"),
                func.count(func.distinct(Submission.challenge_version_id)).label("challenges_solved"),
            )
            .outerjoin(
                Submission,
                (Submission.user_id == User.id) & (Submission.tenant_id == tenant_id),
            )
            .filter(User.tenant_id == tenant_id)
            .group_by(User.id)
            .order_by(func.coalesce(func.sum(Submission.score_awarded), 0).desc())
            .limit(5)
            .all()
        )

        leaderboard = [
            LeaderboardEntry(
                rank=i + 1,
                user_id=str(row.id),
                user_name=row.username,
                username=row.username,
                total_points=float(row.total_points or 0),
                challenges_solved=int(row.challenges_solved or 0),
            )
            for i, row in enumerate(leaderboard_rows)
        ]

        return DashboardResponse(
            user_stats=user_stats,
            last_active_item=last_active_item,
            recommended_next=None,
            todays_mission=None,
            coach_tip=None,
            active_cohorts=[],
            assigned_challenges=[],
            recent_submissions=recent_submissions,
            leaderboard=leaderboard,
            learning=LearningData(),
        )
