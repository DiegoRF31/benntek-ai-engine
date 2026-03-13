"""
AI Player Analytics endpoints — stub implementations pre-wired for Phase 3.

GET  /ai-player-analytics/overview              → summary stats
GET  /ai-player-analytics/anomalies             → detected anomalies + existing flags
GET  /ai-player-analytics/behavior-comparison   → per-personality comparison
POST /ai-player-analytics/anomalies/scan        → trigger anomaly scan
GET  /ai-player-analytics/player/{id}           → per-player detail
POST /ai-player-analytics/anomalies/{id}/resolve → resolve a flag
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import require_role
from app.infrastructure.models.user_model import User
from app.api.ai_players import _PLAYERS  # share in-memory store

router = APIRouter(prefix="/ai-player-analytics", tags=["AI Player Analytics"])

# In-memory flags store for Phase 3
_FLAGS: list[dict] = []
_NEXT_FLAG_ID = 1


@router.get("/overview")
def get_overview(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    tenant_players = [p for p in _PLAYERS if p["tenant_id"] == current_user.tenant_id]
    active = sum(1 for p in tenant_players if p["is_active"])
    total_subs = sum(p["total_attempts"] for p in tenant_players)
    solved = sum(p["challenges_solved"] for p in tenant_players)
    success_rate = round((solved / total_subs * 100), 1) if total_subs > 0 else 0.0

    unresolved = sum(1 for f in _FLAGS if f["tenant_id"] == current_user.tenant_id and not f["resolved"])

    # Personality performance aggregation
    perf_map: dict[str, dict] = {}
    for p in tenant_players:
        pt = p["personality_type"]
        if pt not in perf_map:
            perf_map[pt] = {"player_count": 0, "total_solved": 0, "scores": []}
        perf_map[pt]["player_count"] += 1
        perf_map[pt]["total_solved"] += p["challenges_solved"]
        if p["avg_score"] > 0:
            perf_map[pt]["scores"].append(p["avg_score"])

    personality_performance = [
        {
            "personality_type": pt,
            "player_count": v["player_count"],
            "total_solved": v["total_solved"],
            "avg_score": round(sum(v["scores"]) / len(v["scores"]), 1) if v["scores"] else 0.0,
        }
        for pt, v in perf_map.items()
    ]

    return {
        "overview": {
            "total_players": len(tenant_players),
            "active_players": active,
            "total_submissions": total_subs,
            "success_rate": success_rate,
            "unresolved_anomalies": unresolved,
        },
        "personality_performance": personality_performance,
        "activity_trend": [],  # Phase 3: populated from submissions table
    }


@router.get("/anomalies")
def get_anomalies(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    flags = [f for f in _FLAGS if f["tenant_id"] == current_user.tenant_id and not f["resolved"]]
    existing = [
        {
            "id": f["id"],
            "user_id": str(f["player_id"]),
            "flag_type": f["flag_type"],
            "severity": f["severity"],
            "description": f["description"],
            "evidence": f.get("evidence", ""),
            "flagged_at": f["flagged_at"],
            "player_name": f["player_name"],
        }
        for f in flags
    ]
    return {
        "detected_anomalies": [],   # Phase 3: real-time anomaly detection
        "existing_flags": existing,
    }


@router.get("/behavior-comparison")
def get_behavior_comparison(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    tenant_players = [p for p in _PLAYERS if p["tenant_id"] == current_user.tenant_id]
    comp_map: dict[str, dict] = {}
    for p in tenant_players:
        pt = p["personality_type"]
        if pt not in comp_map:
            comp_map[pt] = {"attempts": 0, "solved": 0, "hint_rates": []}
        comp_map[pt]["attempts"] += p["total_attempts"]
        comp_map[pt]["solved"] += p["challenges_solved"]
        comp_map[pt]["hint_rates"].append(p["hint_usage_rate"])

    comparison = [
        {
            "personality_type": pt,
            "avg_attempts": v["attempts"],
            "avg_solved": v["solved"],
            "avg_hint_rate": round(sum(v["hint_rates"]) / len(v["hint_rates"]), 2) if v["hint_rates"] else 0.0,
        }
        for pt, v in comp_map.items()
    ]
    return {"personality_comparison": comparison}


@router.post("/anomalies/scan")
def scan_anomalies(
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    """
    Stub — Phase 3 will run statistical analysis on submission patterns
    to detect anomalies such as impossible solve times or score spikes.
    """
    return {"scanned": True, "anomalies_found": 0, "message": "Scan complete (Phase 3 will detect real anomalies)"}


@router.get("/player/{player_id}")
def get_player_detail(
    player_id: int,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    player = next(
        (p for p in _PLAYERS if p["id"] == player_id and p["tenant_id"] == current_user.tenant_id),
        None,
    )
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI player not found")

    return {
        "player": {
            "id": player["id"],
            "full_name": player["name"],
            "personality_type": player["personality_type"],
            "skill_level": player["skill_level"],
            "creativity_score": player["creativity_score"],
            "is_active": player["is_active"],
            "total_attempts": player["total_attempts"],
            "challenges_solved": player["challenges_solved"],
            "avg_score": player["avg_score"],
            "last_active": player["last_active"],
        },
        "submissions": [],
        "category_performance": [],
        "difficulty_performance": [],
        "recent_activities": [],
    }


@router.post("/anomalies/{flag_id}/resolve")
def resolve_flag(
    flag_id: int,
    payload: dict,
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    global _FLAGS
    flag = next(
        (f for f in _FLAGS if f["id"] == flag_id and f["tenant_id"] == current_user.tenant_id),
        None,
    )
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    flag["resolved"] = True
    flag["resolution_notes"] = payload.get("resolution_notes", "")
    flag["resolved_at"] = datetime.utcnow().isoformat()
    return {"id": flag_id, "resolved": True}
