from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

class FrameworkItem(BaseModel):
    framework_type: str
    framework_label: str


class ModuleProgress(BaseModel):
    progress_percent: float
    completed_at: Optional[str] = None


class ModuleListItem(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    level: str
    estimated_minutes: Optional[int] = None
    frameworks: List[FrameworkItem]
    section_count: int
    lab_count: int
    progress: Optional[ModuleProgress] = None


class ModulesResponse(BaseModel):
    modules: List[ModuleListItem]


# ---------------------------------------------------------------------------
# Learning Paths
# ---------------------------------------------------------------------------

class PathListItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    level: str
    estimated_hours: Optional[float] = None
    module_count: int
    progress_percent: Optional[float] = None
    completed_modules: Optional[int] = None
    total_modules: Optional[int] = None


class PathsResponse(BaseModel):
    paths: List[PathListItem]
