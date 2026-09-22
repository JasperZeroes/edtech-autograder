"""create submissions

Revision ID: 0003_create_submissions
Revises: 0002_create_assessment_tables
Create Date: 2026-09-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_create_submissions"
down_revision: Union[str, None] = "0002_create_assessment_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
            "attempt_number > 0",
            name="ck_submissions_attempt_number",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_submissions_status",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND failure_reason IS NOT NULL) "
            "OR (status <> 'failed' AND failure_reason IS NULL)",
            name="ck_submissions_failure_reason",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "student_id",
            "attempt_number",
            name="uq_submissions_assignment_student_attempt",
        ),
    )
    op.create_index(
        "ix_submissions_assignment_id",
        "submissions",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        "ix_submissions_status",
        "submissions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_submissions_student_id",
        "submissions",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_submissions_student_id",
        table_name="submissions",
    )
    op.drop_index(
        "ix_submissions_status",
        table_name="submissions",
    )
    op.drop_index(
        "ix_submissions_assignment_id",
        table_name="submissions",
    )
    op.drop_table("submissions")
