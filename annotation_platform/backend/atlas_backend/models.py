"""SQLAlchemy ORM models for the ATLAS backend."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False, default="")
    models_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    conditions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    scans: Mapped[list[Scan]] = relationship("Scan", back_populates="experiment", cascade="all, delete-orphan")
    findings: Mapped[list[Finding]] = relationship("Finding", back_populates="experiment", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    scan_id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False, default="")
    model_short: Mapped[str] = mapped_column(String, nullable=False, default="")
    probe: Mapped[str] = mapped_column(String, nullable=False, default="")
    started_at: Mapped[str] = mapped_column(String, nullable=False, default="")
    completed_at: Mapped[str] = mapped_column(String, nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_target_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_attacker_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    security_score_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    compliance_assessment_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    probe_results_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="scans")

    __table_args__ = (
        Index("ix_scans_experiment", "experiment_id"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False, default="")
    model_short: Mapped[str] = mapped_column(String, nullable=False, default="")
    probe: Mapped[str] = mapped_column(String, nullable=False, default="")
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="")
    prompt_preview: Mapped[str] = mapped_column(String, nullable=False, default="")
    condition: Mapped[str] = mapped_column(String, nullable=False, default="")
    adaptivity: Mapped[str] = mapped_column(String, nullable=False, default="")
    interaction_mode: Mapped[str] = mapped_column(String, nullable=False, default="")
    num_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_target_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_attacker_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    target_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attacker_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detector_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    detail_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="findings")
    annotations: Mapped[list[Annotation]] = relationship("Annotation", back_populates="finding", cascade="all, delete-orphan")
    review_votes: Mapped[list[ReviewVote]] = relationship("ReviewVote", back_populates="finding", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_findings_experiment", "experiment_id"),
        Index("ix_findings_model", "experiment_id", "model"),
        Index("ix_findings_probe", "experiment_id", "probe"),
    )


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    finding: Mapped[Finding] = relationship("Finding", back_populates="annotations")

    __table_args__ = (
        Index("ix_annotations_finding", "finding_id"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    sessions: Mapped[list[Session]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    review_votes: Mapped[list[ReviewVote]] = relationship("ReviewVote", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user", "user_id"),
    )


class ReviewVote(Base):
    __tablename__ = "review_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    finding: Mapped[Finding] = relationship("Finding", back_populates="review_votes")
    user: Mapped[User] = relationship("User", back_populates="review_votes")

    __table_args__ = (
        UniqueConstraint("finding_id", "user_id", name="uq_review_votes_finding_user"),
        Index("ix_review_votes_finding", "finding_id"),
    )
