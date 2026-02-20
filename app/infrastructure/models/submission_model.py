from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Text, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    challenge_version_id: Mapped[int] = mapped_column(
        ForeignKey("challenge_versions.id", ondelete="CASCADE"),
        nullable=False
    )

    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    score_awarded: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    challenge_version = relationship("ChallengeVersion", back_populates="submissions")
    objective_results = relationship("ObjectiveResult", back_populates="submission")
