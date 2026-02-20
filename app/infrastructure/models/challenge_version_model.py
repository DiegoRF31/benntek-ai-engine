from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ChallengeVersion(Base):
    __tablename__ = "challenge_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    challenge_id: Mapped[int] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False
    )

    description: Mapped[str] = mapped_column(String, nullable=False)
    objectives: Mapped[dict] = mapped_column(JSON, nullable=False)
    scoring_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    hints: Mapped[dict] = mapped_column(JSON, nullable=True)
    skills: Mapped[dict] = mapped_column(JSON, nullable=True)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    submissions = relationship("Submission", back_populates="challenge_version")
