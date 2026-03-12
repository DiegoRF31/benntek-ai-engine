from pydantic import BaseModel
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# GET /instructor/challenges response
# ---------------------------------------------------------------------------

class InstructorChallengeItem(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    category: str
    challenge_type: str
    points: float
    time_limit_minutes: Optional[int] = None
    is_published: bool
    created_at: str
    total_submissions: int = 0
    unique_solvers: int = 0
    avg_score: Optional[float] = None
    approval_status: Optional[str] = None       # pending | approved | rejected
    generation_method: Optional[str] = None     # manual | ai_generated
    submitted_at: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewer_name: Optional[str] = None


class InstructorChallengesResponse(BaseModel):
    published: List[InstructorChallengeItem]
    pending: List[InstructorChallengeItem]


# ---------------------------------------------------------------------------
# POST /instructor/challenges/create
# ---------------------------------------------------------------------------

class HintInput(BaseModel):
    text: str = ""
    penalty: float = 0.0


class CreateChallengeRequest(BaseModel):
    title: str
    description: str
    difficulty: str = "beginner"
    category: str = "Prompt Injection"
    challenge_type: str = "prompt_injection"
    points: float = 100.0
    time_limit_minutes: Optional[int] = None
    hints: List[HintInput] = []
    publish_immediately: bool = False


class CreateChallengeResponse(BaseModel):
    success: bool
    challenge_id: int


# ---------------------------------------------------------------------------
# POST /instructor/challenges/generate (save AI-generated draft)
# ---------------------------------------------------------------------------

class AiHintInput(BaseModel):
    hint_level: int
    hint_text: str
    cost_penalty: float


class GenerateDraftRequest(BaseModel):
    title: str
    description: str
    difficulty: str = "beginner"
    category: str = "Prompt Injection"
    challenge_type: str = "llm_sandbox"
    points: float = 100.0
    time_limit_minutes: Optional[int] = None
    config: Any = {}
    hints: List[AiHintInput] = []
    publish_immediately: bool = False


# ---------------------------------------------------------------------------
# POST /instructor/challenges/approve/{id}
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    approve: bool
    notes: Optional[str] = None


class ApproveResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# PUT /instructor/challenges/{id}
# ---------------------------------------------------------------------------

class UpdateChallengeRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    challenge_type: Optional[str] = None
    points: Optional[float] = None
    time_limit_minutes: Optional[int] = None


class UpdateChallengeResponse(BaseModel):
    success: bool
