from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Challenge list
# ---------------------------------------------------------------------------

class ChallengeListItem(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str                 # 'beginner' | 'intermediate' | 'advanced' | 'expert'
    category: str
    challenge_type: str
    points: float
    time_limit_minutes: Optional[int] = None
    user_attempts: int
    user_best_score: float          # percentage 0-100
    user_has_passed: bool


class ChallengeFilters(BaseModel):
    categories: List[str]
    types: List[str]
    difficulties: List[str]


class ChallengeListResponse(BaseModel):
    challenges: List[ChallengeListItem]
    filters: ChallengeFilters


# ---------------------------------------------------------------------------
# Assigned challenges
# ---------------------------------------------------------------------------

class AssignedCohortResponse(BaseModel):
    cohorts: List[Any] = []         # populated in Phase 2 (Cohort model)


# ---------------------------------------------------------------------------
# Challenge detail
# ---------------------------------------------------------------------------

class HintItem(BaseModel):
    id: int
    hint_level: int
    cost_penalty: float
    is_unlocked: bool
    hint_text: Optional[str] = None


class UserProgress(BaseModel):
    attempts: int
    best_score: float               # percentage 0-100
    has_passed: bool


class ChallengeDetail(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    category: str
    challenge_type: str
    points: float
    time_limit_minutes: Optional[int] = None
    config: Any = {}


class ChallengeDetailResponse(BaseModel):
    challenge: ChallengeDetail
    hints: List[HintItem]
    attachments: List[Any] = []
    user_progress: UserProgress


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

class ChallengeSubmissionCreate(BaseModel):
    code: Optional[str] = None
    submission: Optional[str] = None


class SubmissionResult(BaseModel):
    id: int
    attempt_number: int
    score: float
    max_score: float
    status: str
    feedback: str
    has_passed: bool
    submitted_at: str
    execution_time_ms: int


class ChallengeSubmissionResponse(BaseModel):
    submission: SubmissionResult
    hint_penalty: float = 0.0


class SubmissionHistoryResponse(BaseModel):
    submissions: List[SubmissionResult]
