from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.user_model import User
from app.schemas.challenge_authoring_schema import (
    ApproveRequest,
    ApproveResponse,
    CreateChallengeRequest,
    CreateChallengeResponse,
    GenerateDraftRequest,
    InstructorChallengeItem,
    InstructorChallengesResponse,
    UpdateChallengeRequest,
    UpdateChallengeResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_INT = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
_DIFFICULTY_MAP = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert"}


def _map_difficulty(value: int) -> str:
    return _DIFFICULTY_MAP.get(value, "beginner")


def _latest_version(challenge: Challenge) -> Optional[ChallengeVersion]:
    if not challenge.versions:
        return None
    return max(challenge.versions, key=lambda v: v.version_number)


def _next_version_number(challenge: Challenge) -> int:
    if not challenge.versions:
        return 1
    return max(v.version_number for v in challenge.versions) + 1


def _hints_to_json(hints) -> list:
    """Convert form HintInput list to the JSON format stored on ChallengeVersion."""
    result = []
    for i, h in enumerate(hints):
        if hasattr(h, 'text'):
            # CreateChallengeRequest / HintInput format
            result.append({
                "level": i + 1,
                "text": h.text,
                "cost_penalty": float(h.penalty),
            })
        elif hasattr(h, 'hint_text'):
            # AiHintInput format
            result.append({
                "level": h.hint_level,
                "text": h.hint_text,
                "cost_penalty": float(h.cost_penalty),
            })
    return result


def _build_challenge_item(
    challenge: Challenge,
    version: ChallengeVersion,
    total_submissions: int,
    unique_solvers: int,
    avg_score: Optional[float],
) -> InstructorChallengeItem:
    reviewer_name = None
    if version.reviewer:
        reviewer_name = version.reviewer.username

    points = float(sum(version.scoring_rules.values())) if version.scoring_rules else 0.0

    return InstructorChallengeItem(
        id=challenge.id,
        title=challenge.title,
        description=version.description,
        difficulty=_map_difficulty(challenge.difficulty),
        category=challenge.category,
        challenge_type=challenge.challenge_type,
        points=points,
        time_limit_minutes=challenge.time_limit_minutes,
        is_published=version.is_published,
        created_at=challenge.created_at.isoformat(),
        total_submissions=total_submissions,
        unique_solvers=unique_solvers,
        avg_score=avg_score,
        approval_status=version.approval_status,
        generation_method=version.generation_method,
        submitted_at=version.submitted_at.isoformat() if version.submitted_at else None,
        reviewer_notes=version.reviewer_notes,
        reviewer_name=reviewer_name,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ChallengeAuthoringService:

    @staticmethod
    def get_challenges(db: Session, current_user: User) -> InstructorChallengesResponse:
        """
        Instructors see their own challenges.
        Admins see all challenges from all instructors.
        """
        query = db.query(Challenge).filter(Challenge.is_active == True)
        if current_user.role != "admin":
            query = query.filter(Challenge.instructor_id == current_user.id)

        challenges = query.order_by(Challenge.created_at.desc()).all()

        # Batch-load submission stats
        version_ids = [
            v.id
            for c in challenges
            for v in c.versions
        ]

        sub_stats: dict[int, dict] = {}
        if version_ids:
            rows = (
                db.query(
                    Submission.challenge_version_id,
                    func.count(Submission.id).label("total"),
                    func.count(func.distinct(Submission.user_id)).label("unique"),
                    func.avg(Submission.score_awarded).label("avg_score"),
                )
                .filter(Submission.challenge_version_id.in_(version_ids))
                .group_by(Submission.challenge_version_id)
                .all()
            )
            for row in rows:
                sub_stats[row.challenge_version_id] = {
                    "total": row.total or 0,
                    "unique": row.unique or 0,
                    "avg": round(float(row.avg_score), 1) if row.avg_score else None,
                }

        published = []
        pending = []

        for challenge in challenges:
            version = _latest_version(challenge)
            if not version:
                continue

            stats = sub_stats.get(version.id, {"total": 0, "unique": 0, "avg": None})
            item = _build_challenge_item(
                challenge, version,
                total_submissions=stats["total"],
                unique_solvers=stats["unique"],
                avg_score=stats["avg"],
            )

            if version.is_published and version.approval_status == "approved":
                published.append(item)
            else:
                pending.append(item)

        return InstructorChallengesResponse(published=published, pending=pending)

    @staticmethod
    def create_challenge(
        db: Session,
        current_user: User,
        payload: CreateChallengeRequest,
    ) -> CreateChallengeResponse:
        difficulty_int = _DIFFICULTY_INT.get(payload.difficulty, 1)
        hints_json = _hints_to_json(payload.hints)

        # Build a simple single-objective scoring rule from the points value
        scoring_rules = {"objective_1": float(payload.points)}
        objectives = [{"id": 1, "name": "Complete the challenge", "points": float(payload.points)}]

        challenge = Challenge(
            title=payload.title,
            category=payload.category,
            difficulty=difficulty_int,
            is_active=True,
            challenge_type=payload.challenge_type,
            time_limit_minutes=payload.time_limit_minutes,
            instructor_id=current_user.id,
        )
        db.add(challenge)
        db.flush()  # get challenge.id before creating version

        is_published = payload.publish_immediately
        approval_status = "approved" if is_published else "pending"

        version = ChallengeVersion(
            challenge_id=challenge.id,
            description=payload.description,
            objectives=objectives,
            scoring_rules=scoring_rules,
            hints=hints_json if hints_json else None,
            skills=None,
            version_number=1,
            is_published=is_published,
            approval_status=approval_status,
            generation_method="manual",
            submitted_at=datetime.utcnow(),
        )
        db.add(version)
        db.commit()

        return CreateChallengeResponse(success=True, challenge_id=challenge.id)

    @staticmethod
    def generate_draft(
        db: Session,
        current_user: User,
        payload: GenerateDraftRequest,
    ) -> CreateChallengeResponse:
        """Save an AI-generated challenge as a pending draft."""
        difficulty_int = _DIFFICULTY_INT.get(payload.difficulty, 1)
        hints_json = _hints_to_json(payload.hints)

        scoring_rules = {"objective_1": float(payload.points)}
        objectives = [{"id": 1, "name": "Complete the challenge", "points": float(payload.points)}]

        challenge = Challenge(
            title=payload.title,
            category=payload.category,
            difficulty=difficulty_int,
            is_active=True,
            challenge_type=payload.challenge_type,
            time_limit_minutes=payload.time_limit_minutes,
            instructor_id=current_user.id,
        )
        db.add(challenge)
        db.flush()

        is_published = payload.publish_immediately
        approval_status = "approved" if is_published else "pending"

        version = ChallengeVersion(
            challenge_id=challenge.id,
            description=payload.description,
            objectives=objectives,
            scoring_rules=scoring_rules,
            hints=hints_json if hints_json else None,
            skills=None,
            version_number=1,
            is_published=is_published,
            approval_status=approval_status,
            generation_method="ai_generated",
            submitted_at=datetime.utcnow(),
        )
        db.add(version)
        db.commit()

        return CreateChallengeResponse(success=True, challenge_id=challenge.id)

    @staticmethod
    def approve_challenge(
        db: Session,
        current_user: User,
        challenge_id: int,
        payload: ApproveRequest,
    ) -> ApproveResponse:
        """Admin approves or rejects a pending challenge version."""
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        version = _latest_version(challenge)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No version found")

        if version.approval_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Challenge is already {version.approval_status}",
            )

        version.approval_status = "approved" if payload.approve else "rejected"
        version.reviewer_id = current_user.id
        version.reviewer_notes = payload.notes
        if payload.approve:
            version.is_published = True

        db.commit()
        return ApproveResponse(success=True)

    @staticmethod
    def update_challenge(
        db: Session,
        current_user: User,
        challenge_id: int,
        payload: UpdateChallengeRequest,
    ) -> UpdateChallengeResponse:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        # Only the owner or an admin may edit
        if current_user.role != "admin" and challenge.instructor_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        version = _latest_version(challenge)

        if payload.title is not None:
            challenge.title = payload.title
        if payload.category is not None:
            challenge.category = payload.category
        if payload.difficulty is not None:
            challenge.difficulty = _DIFFICULTY_INT.get(payload.difficulty, challenge.difficulty)
        if payload.challenge_type is not None:
            challenge.challenge_type = payload.challenge_type
        if payload.time_limit_minutes is not None:
            challenge.time_limit_minutes = payload.time_limit_minutes

        if version and payload.description is not None:
            version.description = payload.description

        if version and payload.points is not None:
            version.scoring_rules = {"objective_1": float(payload.points)}
            version.objectives = [{"id": 1, "name": "Complete the challenge", "points": float(payload.points)}]

        db.commit()
        return UpdateChallengeResponse(success=True)

    @staticmethod
    def delete_challenge(
        db: Session,
        current_user: User,
        challenge_id: int,
    ) -> None:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")

        if current_user.role != "admin" and challenge.instructor_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Soft delete — keeps submission history intact
        challenge.is_active = False
        db.commit()
