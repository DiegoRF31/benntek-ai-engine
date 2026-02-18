from sqlalchemy import Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

class ChallengeVersion(Base):
    __tablename__ = "challenge_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), nullable=False)

    description: Mapped[dict] = mapped_column(JSONB, nullable=False)
    objectives: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scoring_rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hints: Mapped[dict] = mapped_column(JSONB, nullable=False)
    skills: Mapped[dict] = mapped_column(JSONB, nullable=False)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge", back_populates="versions")
    submissions = relationship("Submission", back_populates="challenge_version")