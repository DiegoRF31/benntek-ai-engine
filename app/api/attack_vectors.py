from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_role
from app.core.database import get_db
from app.infrastructure.models.attack_vector_model import AttackVector
from app.infrastructure.models.user_model import User

router = APIRouter(prefix="/attack-vectors", tags=["Attack Vectors"])

_VALID_SORT = {"created_at", "name", "effectiveness_score", "usage_count"}
_VALID_ORDER = {"asc", "desc"}


def _tenant_query(db: Session, current_user: User):
    return db.query(AttackVector).filter(AttackVector.tenant_id == current_user.id)


@router.get("")
def list_vectors(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    attack_type: Optional[str] = Query(default=None),
    ai_generated: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _tenant_query(db, current_user)

    if search:
        like = f"%{search}%"
        q = q.filter(
            AttackVector.name.ilike(like) | AttackVector.description.ilike(like) | AttackVector.payload.ilike(like)
        )
    if category:
        q = q.filter(AttackVector.category == category)
    if attack_type:
        q = q.filter(AttackVector.attack_type == attack_type)
    if ai_generated is not None:
        q = q.filter(AttackVector.is_ai_generated == (ai_generated.lower() == "true"))

    sort_col = getattr(AttackVector, sort_by if sort_by in _VALID_SORT else "created_at")
    q = q.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    all_vectors = q.all()

    # Category stats
    stats_rows = (
        db.query(
            AttackVector.category,
            func.count(AttackVector.id).label("count"),
            func.avg(AttackVector.effectiveness_score).label("avg_eff"),
            func.sum(AttackVector.usage_count).label("total_usage"),
        )
        .filter(AttackVector.tenant_id == current_user.id)
        .group_by(AttackVector.category)
        .all()
    )
    category_stats = [
        {
            "category": r.category,
            "count": int(r.count),
            "avg_effectiveness": round(float(r.avg_eff or 0), 2),
            "total_usage": int(r.total_usage or 0),
        }
        for r in stats_rows
    ]

    categories = sorted({v.category for v in all_vectors})
    attack_types = sorted({v.attack_type for v in all_vectors})

    return {
        "vectors": [_serialize(v) for v in all_vectors],
        "total": len(all_vectors),
        "category_stats": category_stats,
        "categories": categories,
        "attack_types": attack_types,
    }


@router.get("/export")
def export_vectors(
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _tenant_query(db, current_user)
    if category:
        q = q.filter(AttackVector.category == category)
    vectors = q.all()
    return {
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(vectors),
        "vectors": [_serialize(v) for v in vectors],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_vector(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    vector = AttackVector(
        tenant_id=current_user.id,
        created_by_id=current_user.id,
        name=payload["name"],
        category=payload["category"],
        attack_type=payload.get("attack_type", "direct"),
        payload=payload["payload"],
        description=payload.get("description", ""),
        effectiveness_score=float(payload.get("effectiveness_score", 0.5)),
    )
    db.add(vector)
    db.commit()
    db.refresh(vector)
    return _serialize(vector)


@router.post("/generate")
def generate_vectors(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    """
    Stub — Phase 3 will call Claude API to generate context-aware attack vectors.
    For now inserts sample vectors for the requested category.
    """
    category = payload.get("category", "Prompt Injection")
    count = min(int(payload.get("count", 5)), 20)
    difficulty = payload.get("difficulty", "intermediate")

    samples = [
        {"name": f"[AI] {category} Vector #{i+1}", "attack_type": "direct",
         "payload": f"Ignore previous instructions and {category.lower()} payload #{i+1}",
         "description": f"AI-generated {difficulty} {category} sample vector."}
        for i in range(count)
    ]

    created = []
    for s in samples:
        v = AttackVector(
            tenant_id=current_user.id,
            created_by_id=current_user.id,
            name=s["name"],
            category=category,
            attack_type=s["attack_type"],
            payload=s["payload"],
            description=s["description"],
            effectiveness_score=0.5,
            is_ai_generated=True,
        )
        db.add(v)
        created.append(v)
    db.commit()
    return {"generated": len(created), "category": category}


@router.put("/{vector_id}")
def update_vector(
    vector_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    vector = _tenant_query(db, current_user).filter(AttackVector.id == vector_id).first()
    if not vector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack vector not found")

    for field in ("name", "category", "attack_type", "payload", "description", "effectiveness_score"):
        if field in payload:
            setattr(vector, field, payload[field])
    vector.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vector)
    return _serialize(vector)


@router.delete("/{vector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vector(
    vector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    vector = _tenant_query(db, current_user).filter(AttackVector.id == vector_id).first()
    if not vector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack vector not found")
    db.delete(vector)
    db.commit()


def _serialize(v: AttackVector) -> dict:
    return {
        "id": v.id,
        "name": v.name,
        "category": v.category,
        "attack_type": v.attack_type,
        "payload": v.payload,
        "description": v.description or "",
        "effectiveness_score": v.effectiveness_score,
        "usage_count": v.usage_count,
        "is_ai_generated": v.is_ai_generated,
        "created_at": v.created_at.isoformat() if v.created_at else "",
    }
