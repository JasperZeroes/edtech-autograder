from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.base import Base


class AssignmentModel(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="python",
        server_default="python",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    io_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
        server_default="70",
    )
    unit_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
        server_default="20",
    )
    static_weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )

    max_runtime_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2_000,
        server_default="2000",
    )
    max_memory_kb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=128_000,
        server_default="128000",
    )

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

    io_test_cases: Mapped[list["IOTestCaseModel"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="IOTestCaseModel.order_index, IOTestCaseModel.id",
    )
    unit_test_spec: Mapped["UnitTestSpecificationModel | None"] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
    )
    static_analysis_rules: Mapped["StaticAnalysisRulesModel | None"] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
    )

    __table_args__ = (
        CheckConstraint(
            "language = 'python'",
            name="ck_assignments_language_python",
        ),
        CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_assignments_status",
        ),
        CheckConstraint(
            "io_weight BETWEEN 0 AND 100",
            name="ck_assignments_io_weight",
        ),
        CheckConstraint(
            "unit_weight BETWEEN 0 AND 100",
            name="ck_assignments_unit_weight",
        ),
        CheckConstraint(
            "static_weight BETWEEN 0 AND 100",
            name="ck_assignments_static_weight",
        ),
        CheckConstraint(
            "io_weight + unit_weight + static_weight = 100",
            name="ck_assignments_weight_total",
        ),
        CheckConstraint(
            "max_runtime_ms BETWEEN 100 AND 600000",
            name="ck_assignments_runtime",
        ),
        CheckConstraint(
            "max_memory_kb BETWEEN 16000 AND 2000000",
            name="ck_assignments_memory",
        ),
        Index("ix_assignments_status", "status"),
    )


class IOTestCaseModel(Base):
    __tablename__ = "io_test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stdin: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_stdout: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="hidden",
        server_default="hidden",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    assignment: Mapped[AssignmentModel] = relationship(
        back_populates="io_test_cases"
    )

    __table_args__ = (
        CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_io_test_cases_points",
        ),
        CheckConstraint(
            "visibility IN ('visible', 'hidden')",
            name="ck_io_test_cases_visibility",
        ),
        CheckConstraint(
            "order_index >= 0",
            name="ck_io_test_cases_order",
        ),
    )


class UnitTestSpecificationModel(Base):
    __tablename__ = "unit_test_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_code: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="hidden",
        server_default="hidden",
    )

    assignment: Mapped[AssignmentModel] = relationship(
        back_populates="unit_test_spec"
    )

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            name="uq_unit_test_specs_assignment_id",
        ),
        CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_unit_test_specs_points",
        ),
        CheckConstraint(
            "visibility IN ('visible', 'hidden')",
            name="ck_unit_test_specs_visibility",
        ),
    )


class StaticAnalysisRulesModel(Base):
    __tablename__ = "static_analysis_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    required_functions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )
    forbidden_imports: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )
    max_cyclomatic_complexity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assignment: Mapped[AssignmentModel] = relationship(
        back_populates="static_analysis_rules"
    )

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            name="uq_static_analysis_rules_assignment_id",
        ),
        CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_static_analysis_rules_points",
        ),
        CheckConstraint(
            "max_cyclomatic_complexity IS NULL "
            "OR max_cyclomatic_complexity BETWEEN 1 AND 10000",
            name="ck_static_analysis_rules_complexity",
        ),
    )
