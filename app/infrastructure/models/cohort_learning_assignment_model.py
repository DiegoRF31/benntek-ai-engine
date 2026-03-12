from datetime import datetime
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class CohortLearningAssignment(Base):
    __tablename__ = "cohort_learning_assignments"
    __table_args__ = (
        # One path or one module can be assigned to a cohort only once each
        UniqueConstraint("cohort_id", "learning_path_id", name="uq_cohort_path_assignment"),
        UniqueConstraint("cohort_id", "module_id", name="uq_cohort_module_assignment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_id: Mapped[int] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False
    )
    learning_path_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=True
    )
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), nullable=True
    )
    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cohort = relationship("Cohort", back_populates="learning_assignments")
    learning_path = relationship("LearningPath")
    module = relationship("LearningModule")
    assigned_by = relationship("User")
