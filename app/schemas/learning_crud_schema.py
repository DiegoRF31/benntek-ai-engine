from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

_FRAMEWORK_DISPLAY = {
    "owasp_llm": "OWASP LLM",
    "mitre_atlas": "MITRE ATLAS",
    "nist_ai_rmf": "NIST AI RMF",
    "iso_42001": "ISO 42001",
}


# ---------------------------------------------------------------------------
# Module — request bodies
# ---------------------------------------------------------------------------

class SectionInput(BaseModel):
    id: Optional[int] = None
    section_order: int
    title: str
    content_type: str = "text"
    content: str = ""


class ReferenceInput(BaseModel):
    id: Optional[int] = None
    reference_order: int
    source_type: str = "documentation"
    title: str
    url: str
    description: str = ""


class FrameworkInput(BaseModel):
    framework_type: str
    framework_id: str   # e.g. "LLM01" — stored in framework_label column


class ModuleWriteRequest(BaseModel):
    title: str
    slug: str
    summary: str = ""
    level: str = "beginner"
    estimated_minutes: int = 30
    status: str = "draft"
    prerequisites: str = ""
    learning_outcomes: str = ""
    safety_note: str = ""
    sections: List[SectionInput] = []
    references: List[ReferenceInput] = []
    frameworks: List[FrameworkInput] = []


class ModuleWriteResponse(BaseModel):
    success: bool
    module_id: int


# ---------------------------------------------------------------------------
# Module — single-resource response (GET /learning/modules/{id})
# ModuleDetail.tsx reads data.module, ModuleEditor.tsx reads through api client
# ---------------------------------------------------------------------------

class SectionDetail(BaseModel):
    id: int
    section_order: int
    title: str
    content_type: str
    content: str


class ReferenceDetail(BaseModel):
    id: int
    reference_order: int
    source_type: str
    title: str
    url: str
    description: str


class FrameworkDetail(BaseModel):
    framework_type: str
    framework_id: str       # identifier like "LLM01"
    framework_label: str    # display name like "OWASP LLM"


class ModuleFullDetail(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    level: str
    estimated_minutes: Optional[int] = None
    status: str
    prerequisites: Optional[str] = None
    learning_outcomes: Optional[str] = None
    safety_note: Optional[str] = None
    sections: List[SectionDetail] = []
    references: List[ReferenceDetail] = []
    frameworks: List[FrameworkDetail] = []
    labs: List[Any] = []        # stub until module_lab_links table
    progress: List[Any] = []    # stub until learner_module_progress table


class ModuleDetailResponse(BaseModel):
    module: ModuleFullDetail


# ---------------------------------------------------------------------------
# Path — request bodies
# ---------------------------------------------------------------------------

class PathModuleInput(BaseModel):
    module_id: int
    module_order: int
    is_required: bool = True


class PathWriteRequest(BaseModel):
    title: str
    slug: str
    description: str = ""
    level: str = "beginner"
    estimated_hours: float = 10.0
    status: str = "draft"
    prerequisites: str = ""
    learning_goals: str = ""
    modules: List[PathModuleInput] = []


class PathWriteResponse(BaseModel):
    success: bool
    path_id: int


# ---------------------------------------------------------------------------
# Path — single-resource response (GET /learning/paths/{id})
# PathEditor.tsx reads data.title, data.modules, etc. directly
# ---------------------------------------------------------------------------

class PathModuleDetail(BaseModel):
    module_id: int
    module_order: int
    is_required: bool
    module: Optional[dict] = None   # {id, title, summary, level, estimated_minutes, status}


class PathDetailResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    level: str
    estimated_hours: Optional[float] = None
    status: str
    prerequisites: Optional[str] = None
    learning_goals: Optional[str] = None
    modules: List[PathModuleDetail] = []


# ---------------------------------------------------------------------------
# Section complete stub
# ---------------------------------------------------------------------------

class SectionCompleteResponse(BaseModel):
    success: bool
    message: str = "Progress tracking available in a future release."
