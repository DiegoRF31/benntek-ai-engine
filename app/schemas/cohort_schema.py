from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Cohort list / create
# ---------------------------------------------------------------------------

class CohortItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool
    student_count: int
    challenge_count: int
    created_at: str


class InstructorInfo(BaseModel):
    id: int
    name: str
    email: str
    role: str


class CohortsResponse(BaseModel):
    cohorts: List[CohortItem]
    instructor: InstructorInfo


class CohortCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CohortCreateResponse(BaseModel):
    success: bool
    cohort_id: int


# ---------------------------------------------------------------------------
# Cohort detail
# ---------------------------------------------------------------------------

class StudentItem(BaseModel):
    id: int
    full_name: str
    email: str
    enrolled_at: str
    challenges_completed: int
    total_points: float
    avg_score: float


class ChallengeAssignmentItem(BaseModel):
    id: int
    title: str
    difficulty: str
    category: str
    due_date: Optional[str] = None
    assigned_at: str
    students_attempted: int
    students_completed: int


class CohortDetailResponse(BaseModel):
    cohort: CohortItem
    students: List[StudentItem]
    challenges: List[ChallengeAssignmentItem]


# ---------------------------------------------------------------------------
# Challenge / student assignment
# ---------------------------------------------------------------------------

class AssignChallengeRequest(BaseModel):
    challenge_id: int
    due_date: Optional[str] = None


class EnrollStudentRequest(BaseModel):
    student_id: int


class AvailableChallengeItem(BaseModel):
    id: int
    title: str
    difficulty: str
    category: str


class AvailableStudentItem(BaseModel):
    id: int
    full_name: str
    email: str


class AvailableChallengesResponse(BaseModel):
    challenges: List[AvailableChallengeItem]


class AvailableStudentsResponse(BaseModel):
    students: List[AvailableStudentItem]


# ---------------------------------------------------------------------------
# Instructor analytics
# ---------------------------------------------------------------------------

class CategoryPerformanceItem(BaseModel):
    category: str
    total_submissions: int
    successful_submissions: int
    avg_score: float
    unique_students: int


class EngagementTrendItem(BaseModel):
    date: str
    active_students: int
    total_attempts: int
    successful_attempts: int


class DifficultyStatItem(BaseModel):
    difficulty: str
    assigned_challenges: int
    total_attempts: int
    successful_attempts: int
    avg_score: float


class TopStudentItem(BaseModel):
    full_name: str
    challenges_completed: int
    total_points: float
    avg_score: float


class ChallengeAttentionItem(BaseModel):
    title: str
    difficulty: str
    category: str
    cohort_name: str
    due_date: Optional[str] = None
    students_attempted: int
    students_passed: int
    pass_rate: float


class Recommendation(BaseModel):
    type: str           # success | warning | alert | info
    title: str
    message: str
    action: str


class InstructorAnalyticsResponse(BaseModel):
    categoryPerformance: List[CategoryPerformanceItem]
    engagementTrend: List[EngagementTrendItem]
    difficultyStats: List[DifficultyStatItem]
    topStudents: List[TopStudentItem]
    challengesNeedingAttention: List[ChallengeAttentionItem]
    recommendations: List[Recommendation]
