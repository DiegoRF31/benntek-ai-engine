import re
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.models.learning_module_model import LearningModule, ModuleFramework, ModuleSection
from app.infrastructure.models.learning_path_model import LearningPath, PathModule
from app.infrastructure.models.module_reference_model import ModuleReference
from app.infrastructure.models.user_model import User
from app.schemas.learning_crud_schema import (
    FrameworkDetail,
    ModuleDetailResponse,
    ModuleFullDetail,
    ModuleWriteRequest,
    ModuleWriteResponse,
    PathDetailResponse,
    PathModuleDetail,
    PathModuleInput,
    PathWriteRequest,
    PathWriteResponse,
    ReferenceDetail,
    SectionCompleteResponse,
    SectionDetail,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRAMEWORK_DISPLAY = {
    "owasp_llm": "OWASP LLM",
    "mitre_atlas": "MITRE ATLAS",
    "nist_ai_rmf": "NIST AI RMF",
    "iso_42001": "ISO 42001",
}


def _slug_from_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _ensure_unique_slug(db: Session, slug: str, table, exclude_id: int | None = None) -> str:
    base = slug
    counter = 1
    while True:
        q = db.query(table).filter(table.slug == slug)
        if exclude_id:
            q = q.filter(table.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _module_to_detail(module: LearningModule) -> ModuleFullDetail:
    frameworks = [
        FrameworkDetail(
            framework_type=fw.framework_type,
            framework_id=fw.framework_label,
            framework_label=_FRAMEWORK_DISPLAY.get(fw.framework_type, fw.framework_type),
        )
        for fw in module.frameworks
    ]
    sections = [
        SectionDetail(
            id=s.id,
            section_order=s.section_order,
            title=s.title,
            content_type=s.content_type,
            content=s.content or "",
        )
        for s in module.sections
    ]
    references = [
        ReferenceDetail(
            id=r.id,
            reference_order=r.reference_order,
            source_type=r.source_type,
            title=r.title,
            url=r.url,
            description=r.description or "",
        )
        for r in module.references
    ]
    return ModuleFullDetail(
        id=module.id,
        title=module.title,
        slug=module.slug,
        summary=module.summary,
        level=module.level,
        estimated_minutes=module.estimated_minutes,
        status=module.status,
        prerequisites=module.prerequisites,
        learning_outcomes=module.learning_outcomes,
        safety_note=module.safety_note,
        sections=sections,
        references=references,
        frameworks=frameworks,
        labs=[],
        progress=[],
    )


def _sync_sections(db: Session, module: LearningModule, inputs) -> None:
    """Replace all module sections with the provided inputs (full replace on save)."""
    for s in list(module.sections):
        db.delete(s)
    for inp in inputs:
        db.add(ModuleSection(
            module_id=module.id,
            section_order=inp.section_order,
            title=inp.title,
            content_type=inp.content_type,
            content=inp.content,
        ))


def _sync_references(db: Session, module: LearningModule, inputs) -> None:
    for r in list(module.references):
        db.delete(r)
    for inp in inputs:
        db.add(ModuleReference(
            module_id=module.id,
            reference_order=inp.reference_order,
            source_type=inp.source_type,
            title=inp.title,
            url=inp.url,
            description=inp.description,
        ))


def _sync_frameworks(db: Session, module: LearningModule, inputs) -> None:
    for fw in list(module.frameworks):
        db.delete(fw)
    for inp in inputs:
        db.add(ModuleFramework(
            module_id=module.id,
            framework_type=inp.framework_type,
            framework_label=inp.framework_id,   # store identifier in framework_label column
        ))


def _sync_path_modules(db: Session, path: LearningPath, inputs) -> None:
    for pm in list(path.path_modules):
        db.delete(pm)
    for inp in inputs:
        db.add(PathModule(
            path_id=path.id,
            module_id=inp.module_id,
            module_order=inp.module_order,
            is_required=inp.is_required,
        ))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LearningCrudService:

    # -------------------------------------------------------------------
    # Modules
    # -------------------------------------------------------------------

    @staticmethod
    def get_module_detail(
        db: Session, module_id: int, current_user: User
    ) -> ModuleDetailResponse:
        module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module or module.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
        return ModuleDetailResponse(module=_module_to_detail(module))

    @staticmethod
    def create_module(
        db: Session, current_user: User, payload: ModuleWriteRequest
    ) -> ModuleWriteResponse:
        slug = payload.slug or _slug_from_title(payload.title)
        slug = _ensure_unique_slug(db, slug, LearningModule)

        module = LearningModule(
            tenant_id=current_user.tenant_id,
            title=payload.title,
            slug=slug,
            summary=payload.summary or None,
            level=payload.level,
            estimated_minutes=payload.estimated_minutes or None,
            status=payload.status,
            prerequisites=payload.prerequisites or None,
            learning_outcomes=payload.learning_outcomes or None,
            safety_note=payload.safety_note or None,
        )
        db.add(module)
        db.flush()  # get module.id

        _sync_sections(db, module, payload.sections)
        _sync_references(db, module, payload.references)
        _sync_frameworks(db, module, payload.frameworks)
        db.commit()

        return ModuleWriteResponse(success=True, module_id=module.id)

    @staticmethod
    def update_module(
        db: Session, current_user: User, module_id: int, payload: ModuleWriteRequest
    ) -> ModuleWriteResponse:
        module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module or module.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

        slug = payload.slug or _slug_from_title(payload.title)
        slug = _ensure_unique_slug(db, slug, LearningModule, exclude_id=module.id)

        module.title = payload.title
        module.slug = slug
        module.summary = payload.summary or None
        module.level = payload.level
        module.estimated_minutes = payload.estimated_minutes or None
        module.status = payload.status
        module.prerequisites = payload.prerequisites or None
        module.learning_outcomes = payload.learning_outcomes or None
        module.safety_note = payload.safety_note or None

        _sync_sections(db, module, payload.sections)
        _sync_references(db, module, payload.references)
        _sync_frameworks(db, module, payload.frameworks)
        db.commit()

        return ModuleWriteResponse(success=True, module_id=module.id)

    @staticmethod
    def delete_module(db: Session, current_user: User, module_id: int) -> None:
        module = db.query(LearningModule).filter(LearningModule.id == module_id).first()
        if not module or module.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
        # Soft delete — keeps path associations intact until explicitly cleaned up
        module.status = "archived"
        db.commit()

    @staticmethod
    def complete_section(
        db: Session, current_user: User, module_id: int, section_id: int
    ) -> SectionCompleteResponse:
        # Stub — learner_module_progress table added in Step 12
        return SectionCompleteResponse(success=True)

    # -------------------------------------------------------------------
    # Paths
    # -------------------------------------------------------------------

    @staticmethod
    def get_path_detail(
        db: Session, path_id: int, current_user: User
    ) -> PathDetailResponse:
        path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
        if not path or path.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        path_modules = []
        for pm in path.path_modules:
            mod = pm.module
            module_dict = None
            if mod:
                module_dict = {
                    "id": mod.id,
                    "title": mod.title,
                    "summary": mod.summary,
                    "level": mod.level,
                    "estimated_minutes": mod.estimated_minutes,
                    "status": mod.status,
                }
            path_modules.append(PathModuleDetail(
                module_id=pm.module_id,
                module_order=pm.module_order,
                is_required=pm.is_required,
                module=module_dict,
            ))

        return PathDetailResponse(
            id=path.id,
            title=path.title,
            slug=path.slug,
            description=path.description,
            level=path.level,
            estimated_hours=path.estimated_hours,
            status=path.status,
            prerequisites=path.prerequisites,
            learning_goals=path.learning_goals,
            modules=path_modules,
        )

    @staticmethod
    def create_path(
        db: Session, current_user: User, payload: PathWriteRequest
    ) -> PathWriteResponse:
        slug = payload.slug or _slug_from_title(payload.title)
        slug = _ensure_unique_slug(db, slug, LearningPath)

        path = LearningPath(
            tenant_id=current_user.tenant_id,
            title=payload.title,
            slug=slug,
            description=payload.description or None,
            level=payload.level,
            estimated_hours=payload.estimated_hours or None,
            status=payload.status,
            prerequisites=payload.prerequisites or None,
            learning_goals=payload.learning_goals or None,
        )
        db.add(path)
        db.flush()

        _sync_path_modules(db, path, payload.modules)
        db.commit()

        return PathWriteResponse(success=True, path_id=path.id)

    @staticmethod
    def update_path(
        db: Session, current_user: User, path_id: int, payload: PathWriteRequest
    ) -> PathWriteResponse:
        path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
        if not path or path.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        slug = payload.slug or _slug_from_title(payload.title)
        slug = _ensure_unique_slug(db, slug, LearningPath, exclude_id=path.id)

        path.title = payload.title
        path.slug = slug
        path.description = payload.description or None
        path.level = payload.level
        path.estimated_hours = payload.estimated_hours or None
        path.status = payload.status
        path.prerequisites = payload.prerequisites or None
        path.learning_goals = payload.learning_goals or None

        _sync_path_modules(db, path, payload.modules)
        db.commit()

        return PathWriteResponse(success=True, path_id=path.id)

    @staticmethod
    def delete_path(db: Session, current_user: User, path_id: int) -> None:
        path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
        if not path or path.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        path.status = "archived"
        db.commit()
