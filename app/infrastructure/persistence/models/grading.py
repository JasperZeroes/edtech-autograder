from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.base import Base


class GradingResultModel(Base):
    __tablename__ = "grading_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    io_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    static_weight: Mapped[int] = mapped_column(Integer, nullable=False)

    io_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    unit_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    static_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    io_contribution: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    unit_contribution: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    static_contribution: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    final_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    feedback_facts: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    outcomes: Mapped[list["EvaluationOutcomeModel"]] = relationship(
        back_populates="grading_result",
        cascade="all, delete-orphan",
        order_by="EvaluationOutcomeModel.id",
    )

    __table_args__ = (
        CheckConstraint(
            "io_weight BETWEEN 0 AND 100",
            name="ck_grading_results_io_weight",
        ),
        CheckConstraint(
            "unit_weight BETWEEN 0 AND 100",
            name="ck_grading_results_unit_weight",
        ),
        CheckConstraint(
            "static_weight BETWEEN 0 AND 100",
            name="ck_grading_results_static_weight",
        ),
        CheckConstraint(
            "io_weight + unit_weight + static_weight = 100",
            name="ck_grading_results_weight_total",
        ),
        CheckConstraint(
            "final_score BETWEEN 0 AND 100",
            name="ck_grading_results_final_score",
        ),
    )


class EvaluationOutcomeModel(Base):
    __tablename__ = "evaluation_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grading_result_id: Mapped[int] = mapped_column(
        ForeignKey("grading_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    earned_points: Mapped[int] = mapped_column(Integer, nullable=False)
    possible_points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    grading_result: Mapped[GradingResultModel] = relationship(
        back_populates="outcomes"
    )

    __table_args__ = (
        CheckConstraint(
            "component IN ('io', 'unit', 'static')",
            name="ck_evaluation_outcomes_component",
        ),
        CheckConstraint(
            "status IN ('passed', 'failed', 'error', 'timeout')",
            name="ck_evaluation_outcomes_status",
        ),
        CheckConstraint(
            "earned_points >= 0",
            name="ck_evaluation_outcomes_earned_points",
        ),
        CheckConstraint(
            "possible_points >= 0",
            name="ck_evaluation_outcomes_possible_points",
        ),
        CheckConstraint(
            "earned_points <= possible_points",
            name="ck_evaluation_outcomes_points_order",
        ),
    )
