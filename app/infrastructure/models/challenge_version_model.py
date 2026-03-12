from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, DateTime, Boolean, JSON, Text
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
    hints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    # Authoring workflow
    approval_status: Mapped[str] = mapped_column(String(50), default="approved")   # pending | approved | rejected
    generation_method: Mapped[str] = mapped_column(String(50), default="manual")   # manual | ai_generated
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge", back_populates="versions")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    submissions = relationship("Submission", back_populates="challenge_version")
