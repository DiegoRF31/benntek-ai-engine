from pydantic import BaseModel
from typing import List, Optional


class LeaderboardEntry(BaseModel):
    id: str
    username: str
    rank: int
    total_points: float
    challenges_completed: int
    challenges_attempted: int
    avg_score: Optional[float] = None
    current_streak: int
    last_submission: Optional[str] = None
    total_submissions: int


class GlobalLeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    totalUsers: int = 0
    currentUserRank: Optional[int] = None
    timeframe: str


class CohortInfo(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    student_count: int
    challenge_count: int


class CohortLeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    cohort: Optional[CohortInfo] = None
    totalUsers: int = 0
    currentUserRank: Optional[int] = None


class CohortsResponse(BaseModel):
    cohorts: List[CohortInfo]
