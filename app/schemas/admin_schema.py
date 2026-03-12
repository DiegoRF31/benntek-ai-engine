from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TenantData(BaseModel):
    id: int
    name: str
    slug: str
    subscription_tier: str
    max_users: int
    max_cohorts: int
    is_active: int
    settings: Optional[str] = None
    created_at: str


class TenantStats(BaseModel):
    total_users: int
    admin_count: int
    instructor_count: int
    user_count: int
    total_cohorts: int
    active_cohorts: int
    total_challenges: int
    total_submissions: int


class TenantResponse(BaseModel):
    tenant: TenantData
    stats: TenantStats


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    subscription_tier: Optional[str] = None
    max_users: Optional[int] = None
    max_cohorts: Optional[int] = None
    is_active: Optional[bool] = None
    settings: Optional[str] = None


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class AdminUserItem(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str] = None
    cohort_count: int
    submission_count: int
    avg_score: Optional[float] = None


class AdminUsersResponse(BaseModel):
    users: List[AdminUserItem]


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

class AuditLogItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str


class AuditLogsResponse(BaseModel):
    logs: List[AuditLogItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Anti-cheat flags (stub — no table yet)
# ---------------------------------------------------------------------------

class AntiCheatFlagsResponse(BaseModel):
    flags: List[Any] = []
