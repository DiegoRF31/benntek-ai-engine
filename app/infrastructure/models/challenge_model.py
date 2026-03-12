from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    challenge_type: Mapped[str] = mapped_column(String(100), nullable=False, default="prompt_injection")
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    instructor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    versions = relationship(
        "ChallengeVersion",
        back_populates="challenge",
        cascade="all, delete-orphan"
    )
    instructor = relationship("User", foreign_keys=[instructor_id])