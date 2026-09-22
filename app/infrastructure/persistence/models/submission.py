from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import Base


class SubmissionModel(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        server_default="queued",
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            "attempt_number",
            name="uq_submissions_assignment_student_attempt",
        ),
        CheckConstraint(
            "attempt_number > 0",
            name="ck_submissions_attempt_number",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_submissions_status",
        ),
        CheckConstraint(
            "("
            "status = 'failed' AND failure_reason IS NOT NULL"
            ") OR ("
            "status <> 'failed' AND failure_reason IS NULL"
            ")",
            name="ck_submissions_failure_reason",
        ),
        Index(
            "ix_submissions_student_id",
            "student_id",
        ),
        Index(
            "ix_submissions_assignment_id",
            "assignment_id",
        ),
        Index(
            "ix_submissions_status",
            "status",
        ),
    )
