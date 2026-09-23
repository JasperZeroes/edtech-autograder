"""create grading results

Revision ID: 0004_create_grading_results
Revises: 0003_create_submissions
Create Date: 2026-09-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_create_grading_results"
down_revision: Union[str, None] = "0003_create_submissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grading_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("io_weight", sa.Integer(), nullable=False),
        sa.Column("unit_weight", sa.Integer(), nullable=False),
        sa.Column("static_weight", sa.Integer(), nullable=False),
        sa.Column(
            "io_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "unit_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "static_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "io_contribution",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "unit_contribution",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "static_contribution",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "final_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("feedback_facts", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "io_weight BETWEEN 0 AND 100",
            name="ck_grading_results_io_weight",
        ),
        sa.CheckConstraint(
            "unit_weight BETWEEN 0 AND 100",
            name="ck_grading_results_unit_weight",
        ),
        sa.CheckConstraint(
            "static_weight BETWEEN 0 AND 100",
            name="ck_grading_results_static_weight",
        ),
        sa.CheckConstraint(
            "io_weight + unit_weight + static_weight = 100",
            name="ck_grading_results_weight_total",
        ),
        sa.CheckConstraint(
            "final_score BETWEEN 0 AND 100",
            name="ck_grading_results_final_score",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
    )

    op.create_table(
        "evaluation_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grading_result_id", sa.Integer(), nullable=False),
        sa.Column("component", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("earned_points", sa.Integer(), nullable=False),
        sa.Column("possible_points", sa.Integer(), nullable=False),
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "component IN ('io', 'unit', 'static')",
            name="ck_evaluation_outcomes_component",
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'error', 'timeout')",
            name="ck_evaluation_outcomes_status",
        ),
        sa.CheckConstraint(
            "earned_points >= 0",
            name="ck_evaluation_outcomes_earned_points",
        ),
        sa.CheckConstraint(
            "possible_points >= 0",
            name="ck_evaluation_outcomes_possible_points",
        ),
        sa.CheckConstraint(
            "earned_points <= possible_points",
            name="ck_evaluation_outcomes_points_order",
        ),
        sa.ForeignKeyConstraint(
            ["grading_result_id"],
            ["grading_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_outcomes_grading_result_id",
        "evaluation_outcomes",
        ["grading_result_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_outcomes_grading_result_id",
        table_name="evaluation_outcomes",
    )
    op.drop_table("evaluation_outcomes")
    op.drop_table("grading_results")
