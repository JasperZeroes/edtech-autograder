"""create assessment tables

Revision ID: 0002_create_assessment_tables
Revises: 0001_create_users
Create Date: 2026-09-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_create_assessment_tables"
down_revision: Union[str, None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column(
            "language",
            sa.String(length=32),
            server_default="python",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "io_weight",
            sa.Integer(),
            server_default="70",
            nullable=False,
        ),
        sa.Column(
            "unit_weight",
            sa.Integer(),
            server_default="20",
            nullable=False,
        ),
        sa.Column(
            "static_weight",
            sa.Integer(),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "max_runtime_ms",
            sa.Integer(),
            server_default="2000",
            nullable=False,
        ),
        sa.Column(
            "max_memory_kb",
            sa.Integer(),
            server_default="128000",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language = 'python'",
            name="ck_assignments_language_python",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_assignments_status",
        ),
        sa.CheckConstraint(
            "io_weight BETWEEN 0 AND 100",
            name="ck_assignments_io_weight",
        ),
        sa.CheckConstraint(
            "unit_weight BETWEEN 0 AND 100",
            name="ck_assignments_unit_weight",
        ),
        sa.CheckConstraint(
            "static_weight BETWEEN 0 AND 100",
            name="ck_assignments_static_weight",
        ),
        sa.CheckConstraint(
            "io_weight + unit_weight + static_weight = 100",
            name="ck_assignments_weight_total",
        ),
        sa.CheckConstraint(
            "max_runtime_ms BETWEEN 100 AND 600000",
            name="ck_assignments_runtime",
        ),
        sa.CheckConstraint(
            "max_memory_kb BETWEEN 16000 AND 2000000",
            name="ck_assignments_memory",
        ),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assignments_instructor_id",
        "assignments",
        ["instructor_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignments_status",
        "assignments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "io_test_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("stdin", sa.Text(), nullable=True),
        sa.Column("expected_stdout", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=20),
            server_default="hidden",
            nullable=False,
        ),
        sa.Column(
            "order_index",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_io_test_cases_points",
        ),
        sa.CheckConstraint(
            "visibility IN ('visible', 'hidden')",
            name="ck_io_test_cases_visibility",
        ),
        sa.CheckConstraint(
            "order_index >= 0",
            name="ck_io_test_cases_order",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_io_test_cases_assignment_id",
        "io_test_cases",
        ["assignment_id"],
        unique=False,
    )

    op.create_table(
        "unit_test_specs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("test_code", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=20),
            server_default="hidden",
            nullable=False,
        ),
        sa.CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_unit_test_specs_points",
        ),
        sa.CheckConstraint(
            "visibility IN ('visible', 'hidden')",
            name="ck_unit_test_specs_visibility",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            name="uq_unit_test_specs_assignment_id",
        ),
    )

    op.create_table(
        "static_analysis_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("required_functions", sa.JSON(), nullable=False),
        sa.Column("forbidden_imports", sa.JSON(), nullable=False),
        sa.Column(
            "max_cyclomatic_complexity",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "points BETWEEN 0 AND 100000",
            name="ck_static_analysis_rules_points",
        ),
        sa.CheckConstraint(
            "max_cyclomatic_complexity IS NULL "
            "OR max_cyclomatic_complexity BETWEEN 1 AND 10000",
            name="ck_static_analysis_rules_complexity",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            name="uq_static_analysis_rules_assignment_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("static_analysis_rules")
    op.drop_table("unit_test_specs")
    op.drop_index(
        "ix_io_test_cases_assignment_id",
        table_name="io_test_cases",
    )
    op.drop_table("io_test_cases")
    op.drop_index(
        "ix_assignments_status",
        table_name="assignments",
    )
    op.drop_index(
        "ix_assignments_instructor_id",
        table_name="assignments",
    )
    op.drop_table("assignments")
