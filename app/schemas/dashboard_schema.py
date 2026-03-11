from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Nested schemas
# ---------------------------------------------------------------------------

class SkillRadarItem(BaseModel):
    category: str
    proficiency: float
    fullMark: float = 100.0


class AIRecommendation(BaseModel):
    type: str                       # 'strength' | 'improve' | 'next_challenge'
    title: str
    description: str
    category: Optional[str] = None
    action: Optional[str] = None


class UserStats(BaseModel):
    total_challenges_attempted: int
    total_challenges_solved: int
    challenges_completed: int
    total_points: float
    average_score: float
    current_streak: int
    rank: int
    global_rank: int
    total_users: int
    strong_categories: List[str]
    weak_categories: List[str]
    skill_radar: List[SkillRadarItem]
    ai_recommendations: List[AIRecommendation]


class ChallengeInfo(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str                 # 'beginner' | 'intermediate' | 'advanced' | 'expert'
    category: str
    challenge_type: str
    points: float
    time_limit_minutes: Optional[int] = None
    is_published: bool


class RecentSubmission(BaseModel):
    id: int
    challenge_id: int
    user_id: int
    attempt_number: int
    score: float
    max_score: float
    status: str                     # 'pending' | 'running' | 'completed' | 'failed'
    has_passed: bool
    submitted_at: str
    challenge: ChallengeInfo


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    user_name: str
    username: str
    total_points: float
    challenges_solved: int


class LastActiveItem(BaseModel):
    type: str                       # 'module' | 'challenge'
    id: int
    title: str
    slug: Optional[str] = None
    progress: Optional[float] = None
    estimated_minutes: Optional[int] = None
    passed: Optional[bool] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    url: str


class LearningData(BaseModel):
    assigned_paths: List[Any] = []
    assigned_modules: List[Any] = []


# ---------------------------------------------------------------------------
# Root response — matches frontend DashboardData interface
# ---------------------------------------------------------------------------

class DashboardResponse(BaseModel):
    user_stats: UserStats
    last_active_item: Optional[LastActiveItem] = None
    recommended_next: Optional[Any] = None     # requires AI engine
    todays_mission: Optional[Any] = None       # requires mission system
    coach_tip: Optional[Any] = None            # requires AI engine
    active_cohorts: List[Any] = []             # requires Cohort model
    assigned_challenges: List[Any] = []        # requires Cohort model
    recent_submissions: List[RecentSubmission]
    leaderboard: List[LeaderboardEntry]
    learning: LearningData
