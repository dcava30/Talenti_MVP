"""post_hire_outcomes: track 3/6/12 month post-hire performance snapshots"""

from alembic import op
import sqlalchemy as sa

revision = "0007_post_hire_outcomes"
down_revision = "0006_org_environment_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_hire_outcomes",
        sa.Column("id", sa.String(), nullable=False),
        # FK to interview_scores (the prediction this outcome validates)
        sa.Column("interview_score_id", sa.String(), nullable=False),
        # When was this snapshot recorded
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        # Snapshot cadence: 3_month | 6_month | 12_month | custom
        sa.Column("snapshot_period", sa.String(), nullable=False, server_default="custom"),
        # 1-5 rating: 1=poor, 2=below_expectations, 3=meets, 4=exceeds, 5=exceptional
        sa.Column("outcome_rating", sa.Float(), nullable=False),
        # Free-text notes from hiring manager / HR
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        # Per-dimension ratings JSON: {dimension: 1-5}
        sa.Column("dimension_ratings", sa.Text(), nullable=True),
        # HR / hiring manager who recorded this outcome
        sa.Column("recorded_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["interview_score_id"],
            ["interview_scores.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_post_hire_outcomes_interview_score_id",
        "post_hire_outcomes",
        ["interview_score_id"],
        unique=False,
    )
    op.create_index(
        "ix_post_hire_outcomes_observed_at",
        "post_hire_outcomes",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_post_hire_outcomes_snapshot_period",
        "post_hire_outcomes",
        ["snapshot_period"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_post_hire_outcomes_snapshot_period", table_name="post_hire_outcomes")
    op.drop_index("ix_post_hire_outcomes_observed_at", table_name="post_hire_outcomes")
    op.drop_index("ix_post_hire_outcomes_interview_score_id", table_name="post_hire_outcomes")
    op.drop_table("post_hire_outcomes")
