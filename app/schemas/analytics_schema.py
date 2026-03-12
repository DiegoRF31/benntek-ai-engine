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
