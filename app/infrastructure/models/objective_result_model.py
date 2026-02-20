from sqlalchemy import ForeignKey, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ObjectiveResult(Base):
    __tablename__ = "objective_results"

    id: Mapped[int] = mapped_column(primary_key=True)

    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False
    )

    objective_id: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationship
    submission = relationship("Submission", back_populates="objective_results")
