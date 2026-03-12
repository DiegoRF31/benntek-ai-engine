from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user, require_role
from app.infrastructure.models.user_model import User
from app.application.services.learning_service import LearningService
from app.application.services.learning_crud_service import LearningCrudService
from app.schemas.learning_schema import ModulesResponse, PathsResponse
from app.schemas.learning_crud_schema import (
    ModuleDetailResponse,
    ModuleWriteRequest,
    ModuleWriteResponse,
    PathDetailResponse,
    PathWriteRequest,
    PathWriteResponse,
    SectionCompleteResponse,
)

router = APIRouter(
    prefix="/learning",
    tags=["Learning"],
)


# ===========================================================================
# Learner read-only lists  (published only)
# ===========================================================================

@router.get("/modules", response_model=ModulesResponse)
def get_modules(
    level: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningService.get_modules(db, current_user, level=level, search=search)


@router.get("/paths", response_model=PathsResponse)
def get_paths(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningService.get_paths(db, current_user)


# ===========================================================================
# Single resource detail  (all roles — learner reads, editor populates form)
# ===========================================================================

@router.get("/modules/{module_id}", response_model=ModuleDetailResponse)
def get_module_detail(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningCrudService.get_module_detail(db, module_id, current_user)


@router.get("/paths/{path_id}", response_model=PathDetailResponse)
def get_path_detail(
    path_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningCrudService.get_path_detail(db, path_id, current_user)


# ===========================================================================
# Module CRUD  (instructor / admin only for writes)
# ===========================================================================

@router.post("/modules", response_model=ModuleWriteResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    payload: ModuleWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return LearningCrudService.create_module(db, current_user, payload)


@router.put("/modules/{module_id}", response_model=ModuleWriteResponse)
def update_module(
    module_id: int,
    payload: ModuleWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return LearningCrudService.update_module(db, current_user, module_id, payload)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    LearningCrudService.delete_module(db, current_user, module_id)


# ===========================================================================
# Path CRUD  (instructor / admin only for writes)
# ===========================================================================

@router.post("/paths", response_model=PathWriteResponse, status_code=status.HTTP_201_CREATED)
def create_path(
    payload: PathWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return LearningCrudService.create_path(db, current_user, payload)


@router.put("/paths/{path_id}", response_model=PathWriteResponse)
def update_path(
    path_id: int,
    payload: PathWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    return LearningCrudService.update_path(db, current_user, path_id, payload)


@router.delete("/paths/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path(
    path_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["instructor", "admin"])),
):
    LearningCrudService.delete_path(db, current_user, path_id)


# ===========================================================================
# Section progress  (stub — learner_module_progress table added in Step 12)
# ===========================================================================

@router.post("/modules/{module_id}/sections/{section_id}/complete", response_model=SectionCompleteResponse)
def complete_section(
    module_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LearningCrudService.complete_section(db, current_user, module_id, section_id)


# ===========================================================================
# AI endpoints  (stubs — Phase 4 will wire Claude API)
# ===========================================================================

@router.post("/ai/summarize")
def ai_summarize(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    return {
        "summary": "AI-powered module summarization will be available in Phase 4.",
        "key_points": [],
    }


@router.post("/ai/chat")
def ai_chat(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    return {
        "response": "AI learning assistant will be available in Phase 4.",
        "role": "assistant",
    }


@router.post("/ai/suggest-labs")
def ai_suggest_labs(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    return {
        "labs": [],
        "message": "AI lab suggestions will be available in Phase 4.",
    }
