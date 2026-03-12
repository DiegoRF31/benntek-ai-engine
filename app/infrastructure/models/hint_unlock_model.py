from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class HintUnlock(Base):
    __tablename__ = "user_hint_unlocks"

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_version_id", "hint_id", name="uq_user_hint_unlock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_version_id: Mapped[int] = mapped_column(
        ForeignKey("challenge_versions.id", ondelete="CASCADE"), nullable=False
    )
    # hint_id matches the 1-based id assigned in _build_hints
    hint_id: Mapped[int] = mapped_column(Integer, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    challenge_version = relationship("ChallengeVersion")
