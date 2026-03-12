from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.models.user_model import User
from app.infrastructure.models.learning_module_model import LearningModule, ModuleFramework, ModuleSection
from app.infrastructure.models.learning_path_model import LearningPath, PathModule

from app.schemas.learning_schema import (
    ModuleListItem,
    FrameworkItem,
    ModulesResponse,
    PathListItem,
    PathsResponse,
)

_INSTRUCTOR_ROLES = {"instructor", "admin"}


class LearningService:

    @staticmethod
    def get_modules(
        db: Session,
        current_user: User,
        level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> ModulesResponse:
        # Section count subquery
        section_counts = (
            db.query(
                ModuleSection.module_id,
                func.count(ModuleSection.id).label("section_count"),
            )
            .group_by(ModuleSection.module_id)
            .subquery()
        )

        query = (
            db.query(
                LearningModule,
                func.coalesce(section_counts.c.section_count, 0).label("section_count"),
            )
            .outerjoin(section_counts, section_counts.c.module_id == LearningModule.id)
            .filter(LearningModule.tenant_id == current_user.tenant_id)
        )

        # Instructors/admins see all statuses; learners see only published
        if current_user.role not in _INSTRUCTOR_ROLES:
            query = query.filter(LearningModule.status == "published")
        else:
            # Exclude permanently archived modules from the list view
            query = query.filter(LearningModule.status != "archived")

        if level:
            query = query.filter(LearningModule.level == level)

        if search:
            like = f"%{search}%"
            query = query.filter(
                LearningModule.title.ilike(like) | LearningModule.summary.ilike(like)
            )

        rows = query.order_by(LearningModule.updated_at.desc()).all()

        modules = []
        for module, section_count in rows:
            frameworks = [
                FrameworkItem(
                    framework_type=fw.framework_type,
                    framework_label=fw.framework_label,
                )
                for fw in module.frameworks
            ]

            modules.append(
                ModuleListItem(
                    id=module.id,
                    title=module.title,
                    summary=module.summary,
                    level=module.level,
                    estimated_minutes=module.estimated_minutes,
                    frameworks=frameworks,
                    framework_count=len(frameworks),
                    section_count=int(section_count),
                    lab_count=0,            # module_lab_links table added in a future step
                    status=module.status,
                    created_at=module.created_at.isoformat() if module.created_at else None,
                    progress=None,          # learner_module_progress table added in a future step
                )
            )

        return ModulesResponse(modules=modules)

    @staticmethod
    def get_paths(db: Session, current_user: User) -> PathsResponse:
        # Module count per path subquery
        module_counts = (
            db.query(
                PathModule.path_id,
                func.count(PathModule.id).label("module_count"),
            )
            .group_by(PathModule.path_id)
            .subquery()
        )

        query = (
            db.query(
                LearningPath,
                func.coalesce(module_counts.c.module_count, 0).label("module_count"),
            )
            .outerjoin(module_counts, module_counts.c.path_id == LearningPath.id)
            .filter(LearningPath.tenant_id == current_user.tenant_id)
        )

        if current_user.role not in _INSTRUCTOR_ROLES:
            query = query.filter(LearningPath.status == "published")
        else:
            query = query.filter(LearningPath.status != "archived")

        rows = query.order_by(LearningPath.updated_at.desc()).all()

        paths = [
            PathListItem(
                id=path.id,
                title=path.title,
                description=path.description,
                level=path.level,
                estimated_hours=path.estimated_hours,
                module_count=int(module_count),
                status=path.status,
                created_at=path.created_at.isoformat() if path.created_at else None,
                progress_percent=None,      # learner_module_progress added in a future step
                completed_modules=None,
                total_modules=int(module_count),
            )
            for path, module_count in rows
        ]

        return PathsResponse(paths=paths)
