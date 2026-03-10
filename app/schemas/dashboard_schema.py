from pydantic import BaseModel
from typing import List


class DashboardUser(BaseModel):
    id: int
    email: str
    role: str


class DashboardStats(BaseModel):
    total_users: int
    total_submissions: int


class RecentSubmission(BaseModel):
    id: int
    challenge_version_id: int
    attempt_number: int


class DashboardResponse(BaseModel):
    user: DashboardUser
    stats: DashboardStats
    recent_activity: List[RecentSubmission]