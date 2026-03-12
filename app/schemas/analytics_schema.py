from pydantic import BaseModel
from typing import List, Optional, Any


class ScoreProgressionItem(BaseModel):
    date: str
    avg_score: float
    max_score: float
    submission_count: int


class CategoryScore(BaseModel):
    category: str
    avg_score: float
    min_score: float
    max_score: float
    challenges_attempted: int
    challenges_passed: int


class DifficultyScore(BaseModel):
    difficulty: str
    avg_score: float
    challenges_attempted: int
    challenges_passed: int


class ImprovementItem(BaseModel):
    id: int
    title: str
    category: str
    first_score: float
    best_score: float
    improvement: float


class WeeklyActivity(BaseModel):
    week: str
    active_days: int
    total_submissions: int
    avg_score: float


class LearnerAnalyticsResponse(BaseModel):
    scoreProgression: List[ScoreProgressionItem]
    categoryScores: List[CategoryScore]
    difficultyScores: List[DifficultyScore]
    improvements: List[ImprovementItem]
    percentile: int
    weeklyActivity: List[WeeklyActivity]


# ---------------------------------------------------------------------------
# Instructor cohort score analytics
# ---------------------------------------------------------------------------

class ScoreDistributionItem(BaseModel):
    score_range: str   # "0-59" | "60-69" | "70-79" | "80-89" | "90-100"
    count: int


class CohortProgressItem(BaseModel):
    date: str
    avg_score: float
    max_score: float
    submission_count: int


class StudentPerformanceItem(BaseModel):
    id: int
    full_name: str
    email: str
    avg_score: float
    challenges_attempted: int
    challenges_passed: int
    total_submissions: int


class CategoryBreakdownItem(BaseModel):
    category: str
    avg_score: float
    students_attempted: int
    total_submissions: int
    passed_count: int
    unique_challenges: int


class StrugglingStudentItem(BaseModel):
    id: int
    full_name: str
    email: str
    avg_score: Optional[float] = None
    last_activity: Optional[str] = None


class InstructorCohortScoresResponse(BaseModel):
    scoreDistribution: List[ScoreDistributionItem]
    cohortProgress: List[CohortProgressItem]
    studentPerformance: List[StudentPerformanceItem]
    categoryBreakdown: List[CategoryBreakdownItem]
    strugglingStudents: List[StrugglingStudentItem]
    timeMetrics: List[Any] = []
