from pydantic import BaseModel
from typing import List, Optional, Any


class CohortSummaryItem(BaseModel):
    id: int
    name: str
    total_students: int
    total_assignments: int
    path_assignments: int
    module_assignments: int


class OverviewStats(BaseModel):
    active_learners: int
    completed_modules: int
    total_progress_records: int
    avg_completion_rate: float
    active_last_week: int


class TopPathItem(BaseModel):
    id: int
    title: str
    slug: str
    level: str
    assignments: int
    total_modules: int
    completed_module_instances: int
    students_started: int


class LearningProgressOverviewResponse(BaseModel):
    cohorts: List[CohortSummaryItem]
    stats: OverviewStats
    top_paths: List[TopPathItem]


class StudentProgressItem(BaseModel):
    id: int
    display_name: str
    modules_started: int
    modules_completed: int
    avg_progress: float
    last_activity: Optional[str] = None


class AssignedPathProgressItem(BaseModel):
    assignment_id: int
    id: int
    title: str
    slug: str
    level: str
    total_modules: int
    total_students: int
    students_started: int
    completed_instances: int
    is_required: bool
    due_date: Optional[str] = None


class AssignedModuleProgressItem(BaseModel):
    assignment_id: int
    id: int
    title: str
    slug: str
    level: str
    total_students: int
    students_started: int
    students_completed: int
    avg_completion: float
    is_required: bool
    due_date: Optional[str] = None


class CohortProgressResponse(BaseModel):
    cohort: Any
    students: List[StudentProgressItem]
    assigned_paths: List[AssignedPathProgressItem]
    assigned_modules: List[AssignedModuleProgressItem]
