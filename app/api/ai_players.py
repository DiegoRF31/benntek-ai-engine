"""
AI Players endpoints — stub implementations pre-wired for Phase 3.

GET    /ai-players                  → list AI players for the tenant
GET    /ai-players/personalities    → available personality types
POST   /ai-players                  → create an AI player
PATCH  /ai-players/{id}/toggle      → activate / deactivate
DELETE /ai-players/{id}             → remove
POST   /ai-players/{id}/run-batch   → trigger batch challenge execution (stub)
GET    /ai-players/{id}/stats       → performance stats for one player
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import require_role
from app.core.database import get_db
from app.infrastructure.models.user_model import User

router = APIRouter(prefix="/ai-players", tags=["AI Players"])

# ── Static personality catalogue ──────────────────────────────────────────────
_PERSONALITIES = [
    {
        "type": "aggressive",
        "name": "Aggressive Attacker",
        "description": "Tries every known bypass technique rapidly, high risk / high reward.",
        "skill_level": 8,
        "creativity": 7,
    },
    {
        "type": "methodical",
        "name": "Methodical Analyst",
        "description": "Works systematically through a decision tree before submitting.",
        "skill_level": 7,
        "creativity": 5,
    },
    {
        "type": "creative",
        "name": "Creative Thinker",
        "description": "Relies on novel, lateral-thinking approaches over brute force.",
        "skill_level": 6,
        "creativity": 9,
    },
    {
        "type": "beginner",
        "name": "Novice Learner",
        "description": "Simulates a new learner — makes common mistakes, uses hints often.",
        "skill_level": 3,
        "creativity": 4,
    },
]

# In-memory store for Phase 3 (will move to DB table)
_PLAYERS: list[dict] = []
_NEXT_ID = 1


def _owned_player(player_id: int, tenant_id: int) -> dict:
    p = next((p for p in _PLAYERS if p["id"] == player_id and p["tenant_id"] == tenant_id), None)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI player not found")
    return p


@router.get("/personalities")
def get_personalities(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return {"personalities": _PERSONALITIES}


@router.get("")
def list_players(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    tenant_players = [p for p in _PLAYERS if p["tenant_id"] == current_user.tenant_id]
    return {
        "players": [
            {
                "id": p["id"],
                "user_id": p["id"],
                "personality_type": p["personality_type"],
                "skill_level": p["skill_level"],
                "creativity_score": p["creativity_score"],
                "hint_usage_rate": p["hint_usage_rate"],
                "is_active": p["is_active"],
                "total_attempts": p["total_attempts"],
                "challenges_solved": p["challenges_solved"],
                "avg_score": p["avg_score"],
                "last_active": p["last_active"],
                "full_name": p["name"],
            }
            for p in tenant_players
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_player(
    payload: dict,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    global _NEXT_ID
    personality = next((p for p in _PERSONALITIES if p["type"] == payload.get("personality_type")), None)
    if not personality:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown personality type")

    player = {
        "id": _NEXT_ID,
        "tenant_id": current_user.tenant_id,
        "name": payload.get("name") or personality["name"],
        "personality_type": personality["type"],
        "skill_level": personality["skill_level"],
        "creativity_score": personality["creativity"],
        "hint_usage_rate": 0.3,
        "is_active": True,
        "total_attempts": 0,
        "challenges_solved": 0,
        "avg_score": 0.0,
        "last_active": None,
    }
    _PLAYERS.append(player)
    _NEXT_ID += 1
    return {"id": player["id"], "message": "AI player created"}


@router.patch("/{player_id}/toggle")
def toggle_player(
    player_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    player = _owned_player(player_id, current_user.tenant_id)
    player["is_active"] = not player["is_active"]
    return {"id": player_id, "is_active": player["is_active"]}


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(
    player_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    global _PLAYERS
    _owned_player(player_id, current_user.tenant_id)
    _PLAYERS = [p for p in _PLAYERS if p["id"] != player_id]


@router.post("/{player_id}/run-batch")
def run_batch(
    player_id: int,
    payload: dict,
    current_user: User = Depends(require_role(["instructor", "admin"])),
    db: Session = Depends(get_db),
):
    """
    Stub — Phase 3 will execute the AI player against real challenges using
    the Claude API and record submissions to the submissions table.
    """
    player = _owned_player(player_id, current_user.tenant_id)
    max_challenges = int(payload.get("max_challenges", 5))
    # Simulate results
    player["total_attempts"] += max_challenges
    player["last_active"] = datetime.utcnow().isoformat()
    return {
        "executed": max_challenges,
        "player_id": player_id,
        "message": f"Batch run simulated ({max_challenges} challenges). Phase 3 will submit real attempts.",
    }


@router.get("/{player_id}/stats")
def get_player_stats(
    player_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    player = _owned_player(player_id, current_user.tenant_id)
    return {
        "stats": {
            "total_attempts": player["total_attempts"],
            "challenges_solved": player["challenges_solved"],
            "avg_score": player["avg_score"],
            "hint_usage_rate": player["hint_usage_rate"],
            "last_active": player["last_active"],
        },
        "category_performance": [],
        "recent_activity": [],
    }
