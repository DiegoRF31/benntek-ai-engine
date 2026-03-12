from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.infrastructure.models.user_model import User
from app.infrastructure.models.submission_model import Submission
from app.infrastructure.models.challenge_model import Challenge
from app.api.auth import require_role

from app.schemas.admin_schema import (
    TenantResponse,
    TenantData,
    TenantStats,
    TenantUpdateRequest,
    AdminUserItem,
    AdminUsersResponse,
    UserUpdateRequest,
    AuditLogsResponse,
    AntiCheatFlagsResponse,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

@router.get("/tenant", response_model=TenantResponse)
def get_tenant(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    tid = current_user.tenant_id

    def _count_role(role: str) -> int:
        return (
            db.query(func.count(User.id))
            .filter(User.tenant_id == tid, User.role == role)
            .scalar() or 0
        )

    total_users = db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar() or 0
    total_challenges = db.query(func.count(Challenge.id)).scalar() or 0
    total_submissions = (
        db.query(func.count(Submission.id))
        .join(User, User.id == Submission.user_id)
        .filter(User.tenant_id == tid)
        .scalar() or 0
    )

    tenant = TenantData(
        id=tid or 1,
        name=f"Tenant {tid}",
        slug=f"tenant-{tid}",
        subscription_tier="professional",
        max_users=100,
        max_cohorts=10,
        is_active=1,
        settings=None,
        created_at=datetime.utcnow().isoformat(),
    )

    stats = TenantStats(
        total_users=total_users,
        admin_count=_count_role("admin"),
        instructor_count=_count_role("instructor"),
        user_count=_count_role("user"),
        total_cohorts=0,
        active_cohorts=0,
        total_challenges=total_challenges,
        total_submissions=total_submissions,
    )

    return TenantResponse(tenant=tenant, stats=stats)


@router.put("/tenant")
def update_tenant(
    body: TenantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    # No tenants table yet — acknowledge without persisting
    return {"success": True}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users", response_model=AdminUsersResponse)
def get_all_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    sub_stats = (
        db.query(
            Submission.user_id,
            func.count(Submission.id).label("submission_count"),
            func.avg(Submission.score_awarded).label("avg_score"),
        )
        .group_by(Submission.user_id)
        .subquery()
    )

    query = (
        db.query(
            User,
            func.coalesce(sub_stats.c.submission_count, 0).label("submission_count"),
            sub_stats.c.avg_score,
        )
        .outerjoin(sub_stats, sub_stats.c.user_id == User.id)
        .filter(User.tenant_id == current_user.tenant_id)
    )

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    rows = query.order_by(User.created_at.desc()).all()

    users = [
        AdminUserItem(
            id=u.id,
            email=u.email,
            full_name=u.username,
            role=u.role,
            is_active=bool(u.is_active),
            created_at=u.created_at.isoformat() if u.created_at else "",
            last_login_at=None,
            cohort_count=0,
            submission_count=int(submission_count),
            avg_score=round(float(avg_score), 2) if avg_score else None,
        )
        for u, submission_count, avg_score in rows
    ]

    return AdminUsersResponse(users=users)


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    return {"success": True}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Audit logs  (no audit_logs table yet — returns empty stub)
# ---------------------------------------------------------------------------

@router.get("/audit-logs", response_model=AuditLogsResponse)
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    return AuditLogsResponse(logs=[], total=0, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Anti-cheat flags  (no anti_cheat_flags table yet — returns empty stub)
# ---------------------------------------------------------------------------

@router.get("/anti-cheat-flags", response_model=AntiCheatFlagsResponse)
def get_anti_cheat_flags(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    return AntiCheatFlagsResponse(flags=[])
