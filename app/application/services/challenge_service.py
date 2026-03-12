from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion
from app.infrastructure.models.hint_unlock_model import HintUnlock
from app.infrastructure.models.objective_result_model import ObjectiveResult
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.user_model import User
from app.schemas.challenge_schema import (
    AssignedCohortResponse,
    ChallengeDetail,
    ChallengeDetailResponse,
    ChallengeFilters,
    ChallengeListItem,
    ChallengeListResponse,
    ChallengeSubmissionCreate,
    ChallengeSubmissionResponse,
    HintItem,
    HintsResponse,
    HintUnlockResponse,
    ObjectiveResultItem,
    SolutionDownloadResponse,
    SubmissionHistoryResponse,
    SubmissionResult,
    TestResultsResponse,
    UserProgress,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_MAP = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert"}
_DIFFICULTY_INT = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}


def _map_difficulty(value: int) -> str:
    return _DIFFICULTY_MAP.get(value, "beginner")


def _compute_points(scoring_rules: dict) -> float:
    if not scoring_rules:
        return 0.0
    return float(sum(scoring_rules.values()))


def _latest_published_version(challenge: Challenge) -> Optional[ChallengeVersion]:
    published = [v for v in challenge.versions if v.is_published]
    if not published:
        return None
    return max(published, key=lambda v: v.version_number)


def _build_hints(raw_hints, unlocked_ids: set[int] | None = None) -> list[HintItem]:
    """Build HintItem list from the JSON stored on ChallengeVersion.hints.

    raw_hints may be a list of dicts or a dict keyed by string index.
    unlocked_ids is the set of hint_id values the current user has unlocked;
    when None (detail view before a separate fetch) all hints are locked.
    """
    hints = []
    if not raw_hints:
        return hints

    unlocked = unlocked_ids or set()

    if isinstance(raw_hints, list):
        for i, h in enumerate(raw_hints):
            if isinstance(h, dict):
                hint_id = i + 1
                is_unlocked = hint_id in unlocked
                hints.append(HintItem(
                    id=hint_id,
                    hint_level=h.get("level", hint_id),
                    cost_penalty=float(h.get("cost_penalty", 0.0)),
                    is_unlocked=is_unlocked,
                    hint_text=h.get("text") if is_unlocked else None,
                ))
    elif isinstance(raw_hints, dict):
        for key, h in raw_hints.items():
            hint_id = int(key)
            is_unlocked = hint_id in unlocked
            hints.append(HintItem(
                id=hint_id,
                hint_level=hint_id,
                cost_penalty=float(h.get("cost_penalty", 0.0)) if isinstance(h, dict) else 0.0,
                is_unlocked=is_unlocked,
                hint_text=h.get("text") if (is_unlocked and isinstance(h, dict)) else None,
            ))

    return sorted(hints, key=lambda h: h.hint_level)


def _get_unlocked_ids(db: Session, user_id: int, version_id: int) -> set[int]:
    rows = (
        db.query(HintUnlock.hint_id)
        .filter(
            HintUnlock.user_id == user_id,
            HintUnlock.challenge_version_id == version_id,
        )
        .all()
    )
    return {r.hint_id for r in rows}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ChallengeService:

    @staticmethod
    def list_challenges(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        challenge_type: Optional[str] = None,
    ) -> ChallengeListResponse:

        query = db.query(Challenge).filter(Challenge.is_active == True)

        if category:
            query = query.filter(Challenge.category == category)
        if difficulty and difficulty in _DIFFICULTY_INT:
            query = query.filter(Challenge.difficulty == _DIFFICULTY_INT[difficulty])
        if search:
            query = query.filter(Challenge.title.ilike(f"%{search}%"))

        all_challenges = query.all()

        # Keep only challenges with at least one published version
        pairs = [
            (c, _latest_published_version(c))
            for c in all_challenges
        ]
        pairs = [(c, v) for c, v in pairs if v is not None]

        # Fetch all user submissions once
        user_subs = (
            db.query(Submission)
            .filter(Submission.user_id == current_user.id)
            .all()
        )
        version_subs: dict[int, list] = {}
        for sub in user_subs:
            version_subs.setdefault(sub.challenge_version_id, []).append(sub)

        items = []
        for challenge, version in pairs:
            subs = version_subs.get(version.id, [])
            max_pts = _compute_points(version.scoring_rules)
            attempts = len(subs)
            best_score = 0.0
            if subs and max_pts > 0:
                best_score = round(
                    max(s.score_awarded or 0.0 for s in subs) / max_pts * 100, 1
                )
            has_passed = any((s.score_awarded or 0.0) > 0 for s in subs)

            items.append(ChallengeListItem(
                id=challenge.id,
                title=challenge.title,
                description=version.description,
                difficulty=_map_difficulty(challenge.difficulty),
                category=challenge.category,
                challenge_type="prompt_injection",
                points=max_pts,
                time_limit_minutes=None,
                user_attempts=attempts,
                user_best_score=best_score,
                user_has_passed=has_passed,
            ))

        # Build filter options from all active challenges (unfiltered)
        all_active = db.query(Challenge).filter(Challenge.is_active == True).all()
        categories = sorted(set(c.category for c in all_active))
        diff_order = list(_DIFFICULTY_MAP.values())
        difficulties = sorted(
            set(_map_difficulty(c.difficulty) for c in all_active),
            key=lambda d: diff_order.index(d) if d in diff_order else 99,
        )

        return ChallengeListResponse(
            challenges=items,
            filters=ChallengeFilters(
                categories=categories,
                types=["prompt_injection"],
                difficulties=difficulties,
            ),
        )

    @staticmethod
    def get_assigned(db: Session, current_user: User) -> AssignedCohortResponse:
        return AssignedCohortResponse(cohorts=[])

    @staticmethod
    def get_challenge_detail(
        db: Session, challenge_id: int, current_user: User
    ) -> Optional[ChallengeDetailResponse]:

        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            return None

        version = _latest_published_version(challenge)
        if not version:
            return None

        points = _compute_points(version.scoring_rules)
        unlocked_ids = _get_unlocked_ids(db, current_user.id, version.id)
        hints = _build_hints(version.hints, unlocked_ids)

        subs = (
            db.query(Submission)
            .filter(
                Submission.user_id == current_user.id,
                Submission.challenge_version_id == version.id,
            )
            .all()
        )
        attempts = len(subs)
        best_score = 0.0
        if subs and points > 0:
            best_score = round(
                max(s.score_awarded or 0.0 for s in subs) / points * 100, 1
            )
        has_passed = any((s.score_awarded or 0.0) > 0 for s in subs)

        return ChallengeDetailResponse(
            challenge=ChallengeDetail(
                id=challenge.id,
                title=challenge.title,
                description=version.description,
                difficulty=_map_difficulty(challenge.difficulty),
                category=challenge.category,
                challenge_type="prompt_injection",
                points=points,
                time_limit_minutes=None,
                config={},
            ),
            hints=hints,
            attachments=[],
            user_progress=UserProgress(
                attempts=attempts,
                best_score=best_score,
                has_passed=has_passed,
            ),
        )

    @staticmethod
    def get_submission_history(
        db: Session, challenge_id: int, current_user: User
    ) -> SubmissionHistoryResponse:

        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            return SubmissionHistoryResponse(submissions=[])

        version = _latest_published_version(challenge)
        if not version:
            return SubmissionHistoryResponse(submissions=[])

        max_pts = _compute_points(version.scoring_rules)

        subs = (
            db.query(Submission)
            .filter(
                Submission.user_id == current_user.id,
                Submission.challenge_version_id == version.id,
            )
            .order_by(Submission.created_at.desc())
            .all()
        )

        results = [
            SubmissionResult(
                id=s.id,
                attempt_number=s.attempt_number,
                score=s.score_awarded or 0.0,
                max_score=max_pts,
                status="completed",
                feedback="",
                has_passed=(s.score_awarded or 0.0) > 0,
                submitted_at=s.created_at.isoformat(),
                execution_time_ms=0,
            )
            for s in subs
        ]

        return SubmissionHistoryResponse(submissions=results)

    @staticmethod
    def create_submission(
        db: Session,
        challenge_id: int,
        current_user: User,
        payload: ChallengeSubmissionCreate,
    ) -> ChallengeSubmissionResponse:

        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        version = _latest_published_version(challenge)
        if not version:
            raise HTTPException(status_code=404, detail="No published version for this challenge")

        max_pts = _compute_points(version.scoring_rules)

        prev_count = (
            db.query(func.count(Submission.id))
            .filter(
                Submission.user_id == current_user.id,
                Submission.challenge_version_id == version.id,
            )
            .scalar() or 0
        )
        attempt_number = prev_count + 1

        submission_text = payload.code or payload.submission or ""
        # Placeholder scoring — real AI evaluation added in Phase 3
        score = round(min(max_pts * 0.1, 0.0), 2)  # always 0 until real scorer

        sub = Submission(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            challenge_version_id=version.id,
            input_text=submission_text,
            attempt_number=attempt_number,
            score_awarded=score,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        return ChallengeSubmissionResponse(
            submission=SubmissionResult(
                id=sub.id,
                attempt_number=sub.attempt_number,
                score=sub.score_awarded or 0.0,
                max_score=max_pts,
                status="completed",
                feedback="Submission recorded. Full AI evaluation coming in Phase 3.",
                has_passed=False,
                submitted_at=sub.created_at.isoformat(),
                execution_time_ms=0,
            ),
            hint_penalty=0.0,
        )

    # -----------------------------------------------------------------------
    # Hints
    # -----------------------------------------------------------------------

    @staticmethod
    def get_hints(
        db: Session, challenge_id: int, current_user: User
    ) -> HintsResponse:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        version = _latest_published_version(challenge)
        if not version:
            raise HTTPException(status_code=404, detail="No published version for this challenge")

        unlocked_ids = _get_unlocked_ids(db, current_user.id, version.id)
        hints = _build_hints(version.hints, unlocked_ids)
        return HintsResponse(hints=hints)

    @staticmethod
    def unlock_hint(
        db: Session, challenge_id: int, hint_id: int, current_user: User
    ) -> HintUnlockResponse:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        version = _latest_published_version(challenge)
        if not version:
            raise HTTPException(status_code=404, detail="No published version for this challenge")

        # Build hints to validate hint_id and get cost
        all_hints = _build_hints(version.hints)
        target = next((h for h in all_hints if h.id == hint_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Hint not found")

        # Check already unlocked
        existing = (
            db.query(HintUnlock)
            .filter(
                HintUnlock.user_id == current_user.id,
                HintUnlock.challenge_version_id == version.id,
                HintUnlock.hint_id == hint_id,
            )
            .first()
        )
        if existing:
            # Return already-unlocked hint with its text
            unlocked_ids = _get_unlocked_ids(db, current_user.id, version.id)
            hints = _build_hints(version.hints, unlocked_ids)
            unlocked_hint = next(h for h in hints if h.id == hint_id)
            return HintUnlockResponse(
                success=True, hint=unlocked_hint, penalty_applied=0.0
            )

        # Insert unlock record
        unlock = HintUnlock(
            user_id=current_user.id,
            challenge_version_id=version.id,
            hint_id=hint_id,
        )
        db.add(unlock)
        db.commit()

        # Return the hint with text revealed
        unlocked_ids = _get_unlocked_ids(db, current_user.id, version.id)
        hints = _build_hints(version.hints, unlocked_ids)
        unlocked_hint = next(h for h in hints if h.id == hint_id)
        return HintUnlockResponse(
            success=True,
            hint=unlocked_hint,
            penalty_applied=target.cost_penalty,
        )

    # -----------------------------------------------------------------------
    # Test results
    # -----------------------------------------------------------------------

    @staticmethod
    def get_test_results(
        db: Session, challenge_id: int, current_user: User
    ) -> TestResultsResponse:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        version = _latest_published_version(challenge)
        if not version:
            raise HTTPException(status_code=404, detail="No published version for this challenge")

        max_pts = _compute_points(version.scoring_rules)

        # Most recent submission by this user for this challenge version
        last_sub = (
            db.query(Submission)
            .filter(
                Submission.user_id == current_user.id,
                Submission.challenge_version_id == version.id,
            )
            .order_by(Submission.created_at.desc())
            .first()
        )

        if last_sub is None:
            return TestResultsResponse(
                submission_id=None,
                score=0.0,
                max_score=max_pts,
                objectives=[],
            )

        # Build a label lookup from the objectives JSON
        # Supports list format: [{id, name, points}, ...] or dict: {id: {name, points}}
        raw_objectives = version.objectives or {}
        label_map: dict[int, tuple[str, float]] = {}  # objective_id → (label, max_points)
        if isinstance(raw_objectives, list):
            for obj in raw_objectives:
                if isinstance(obj, dict):
                    oid = int(obj.get("id", 0))
                    label_map[oid] = (str(obj.get("name", f"Objective {oid}")), float(obj.get("points", 0.0)))
        elif isinstance(raw_objectives, dict):
            for key, obj in raw_objectives.items():
                oid = int(key)
                if isinstance(obj, dict):
                    label_map[oid] = (str(obj.get("name", f"Objective {oid}")), float(obj.get("points", 0.0)))

        # Load objective results for last submission
        obj_results = (
            db.query(ObjectiveResult)
            .filter(ObjectiveResult.submission_id == last_sub.id)
            .all()
        )

        objectives = []
        for result in obj_results:
            label, max_obj_pts = label_map.get(result.objective_id, (f"Objective {result.objective_id}", 0.0))
            objectives.append(ObjectiveResultItem(
                objective_id=result.objective_id,
                label=label,
                passed=result.passed,
                points_awarded=result.points_awarded,
                max_points=max_obj_pts,
            ))

        return TestResultsResponse(
            submission_id=last_sub.id,
            score=last_sub.score_awarded or 0.0,
            max_score=max_pts,
            objectives=objectives,
        )

    # -----------------------------------------------------------------------
    # Solution download
    # -----------------------------------------------------------------------

    @staticmethod
    def get_solution_download(
        db: Session, challenge_id: int, current_user: User
    ) -> SolutionDownloadResponse:
        challenge = (
            db.query(Challenge)
            .filter(Challenge.id == challenge_id, Challenge.is_active == True)
            .first()
        )
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        version = _latest_published_version(challenge)
        if not version:
            raise HTTPException(status_code=404, detail="No published version for this challenge")

        slug = challenge.title.lower().replace(" ", "_")
        template = (
            f"# Solution template for: {challenge.title}\n"
            f"# Category: {challenge.category}\n"
            f"# Difficulty: {_map_difficulty(challenge.difficulty)}\n"
            f"#\n"
            f"# Description:\n"
            f"# {version.description}\n\n"
            f"# Write your solution below:\n\n"
        )

        return SolutionDownloadResponse(
            filename=f"{slug}_solution.txt",
            content=template,
            content_type="text/plain",
        )
