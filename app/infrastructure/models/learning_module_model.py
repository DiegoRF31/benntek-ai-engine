from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class LearningModule(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(String(50), nullable=False)          # beginner|intermediate|advanced|expert
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")        # draft|in_review|published
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    frameworks = relationship("ModuleFramework", back_populates="module", cascade="all, delete-orphan")
    sections = relationship("ModuleSection", back_populates="module", cascade="all, delete-orphan")


class ModuleFramework(Base):
    __tablename__ = "module_frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    framework_type: Mapped[str] = mapped_column(String(100), nullable=False)    # owasp_llm|mitre_atlas|nist_ai_rmf|iso_42001
    framework_label: Mapped[str] = mapped_column(String(255), nullable=False)

    module = relationship("LearningModule", back_populates="frameworks")


class ModuleSection(Base):
    __tablename__ = "module_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    module = relationship("LearningModule", back_populates="sections")
