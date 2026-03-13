"""
Coaching endpoints — stub implementations pre-wired for Phase 4 LLM integration.

GET  /coaching/profile           → real performance data from submissions
GET  /coaching/recommendations   → stub; Phase 4 will call Claude API
POST /coaching/session/start     → stub session creation
POST /coaching/session/{id}/chat → stub; Phase 4 will stream Claude responses
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.infrastructure.models.challenge_version_model import ChallengeVersion

router = APIRouter(prefix="/coaching", tags=["Coaching"])

_PASS_THRESHOLD = 70.0


@router.get("/profile")
def get_coaching_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns real performance data for the current learner."""
    subs = (
        db.query(Submission)
        .filter(
            Submission.user_id == current_user.id,
            Submission.score_awarded.isnot(None),
        )
        .all()
    )

    total_submissions = len(subs)
    avg_score = (
        sum(s.score_awarded for s in subs) / total_submissions
        if total_submissions > 0
        else 0.0
    )

    # Unique challenges attempted / completed (best score >= threshold)
    version_ids = list({s.challenge_version_id for s in subs})
    best_per_version: dict[int, float] = {}
    for s in subs:
        vid = s.challenge_version_id
        if vid not in best_per_version or s.score_awarded > best_per_version[vid]:
            best_per_version[vid] = s.score_awarded

    challenges_attempted = len(best_per_version)
    challenges_completed = sum(1 for sc in best_per_version.values() if sc >= _PASS_THRESHOLD)

    # Category breakdown
    category_data: dict[str, dict] = {}
    if version_ids:
        rows = (
            db.query(
                Challenge.category,
                ChallengeVersion.id.label("version_id"),
                func.max(Submission.score_awarded).label("best"),
                func.avg(Submission.score_awarded).label("avg"),
            )
            .join(ChallengeVersion, Submission.challenge_version_id == ChallengeVersion.id)
            .join(Challenge, ChallengeVersion.challenge_id == Challenge.id)
            .filter(
                Submission.user_id == current_user.id,
                Submission.score_awarded.isnot(None),
            )
            .group_by(Challenge.category, ChallengeVersion.id)
            .all()
        )

        for row in rows:
            cat = row.category or "Uncategorized"
            if cat not in category_data:
                category_data[cat] = {"attempted": 0, "completed": 0, "scores": []}
            category_data[cat]["attempted"] += 1
            if (row.best or 0) >= _PASS_THRESHOLD:
                category_data[cat]["completed"] += 1
            category_data[cat]["scores"].append(float(row.avg or 0))

    categories = [
        {
            "category": cat,
            "attempted": data["attempted"],
            "completed": data["completed"],
            "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0.0,
        }
        for cat, data in category_data.items()
    ]

    # Derive strengths / weaknesses from category performance
    sorted_cats = sorted(categories, key=lambda c: c["avg_score"], reverse=True)
    strengths = [c["category"] for c in sorted_cats[:2]] if sorted_cats else []
    weaknesses = [c["category"] for c in sorted_cats[-2:] if c["avg_score"] < _PASS_THRESHOLD] if sorted_cats else []

    return {
        "performance": {
            "challenges_completed": challenges_completed,
            "challenges_attempted": challenges_attempted,
            "avg_score": round(avg_score, 1),
            "total_points": round(avg_score * challenges_completed, 0),
            "total_submissions": total_submissions,
        },
        "categories": categories,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recent_sessions": [],  # Phase 4: persisted coaching sessions
    }


@router.get("/recommendations")
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stub — returns static recommendations.
    Phase 4 will call Claude API with the user's profile as context.
    """
    available_challenges = (
        db.query(Challenge.id, Challenge.title, Challenge.category, Challenge.difficulty)
        .filter(Challenge.is_active == True)
        .limit(5)
        .all()
    )

    return {
        "recommendations": {
            "overall_assessment": "You're building a solid foundation in AI security. Keep pushing your limits with more advanced challenges.",
            "strengths": ["Persistence", "Problem-solving approach"],
            "improvement_areas": ["Advanced prompt injection", "Multi-turn jailbreaking"],
            "recommended_focus": "Focus on intermediate prompt injection challenges to bridge the gap to advanced techniques.",
            "learning_path": [
                {"step": 1, "action": "Complete 3 intermediate prompt injection challenges", "reason": "Builds pattern recognition for bypass techniques"},
                {"step": 2, "action": "Study jailbreaking via role-play framing", "reason": "High success rate among similar learners"},
                {"step": 3, "action": "Attempt an expert-level challenge", "reason": "Tests consolidated knowledge under pressure"},
            ],
            "daily_goals": [
                "Attempt at least one new challenge",
                "Review hints only after 3 genuine attempts",
                "Note what worked and what didn't after each session",
            ],
            "motivation_message": "Every failed attempt is data. You're closer than you think.",
        },
        "available_challenges": [
            {"id": c.id, "title": c.title, "category": c.category, "difficulty": c.difficulty}
            for c in available_challenges
        ],
    }


@router.post("/session/start")
def start_session(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Stub — returns a mock session ID.
    Phase 4 will persist this session and inject the user's profile as Claude context.
    """
    return {"sessionId": 1, "session_type": payload.get("sessionType", "general")}


@router.post("/session/{session_id}/chat")
def chat(
    session_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Stub — echoes a static response.
    Phase 4 will stream a Claude API response using the session's conversation history.
    """
    user_message = payload.get("message", "")
    return {
        "conversation": [
            {
                "role": "assistant",
                "content": (
                    "Great question! In Phase 4, I'll be powered by Claude and will give you "
                    "personalised guidance based on your submission history. For now, I'd suggest "
                    "focusing on the challenge categories where your average score is below 70 — "
                    "those are your biggest growth opportunities."
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]
    }
