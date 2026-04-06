"""dual_scorecard_columns: rename overall_score to culture_fit_score, add skills_score and skills_outcome"""

from alembic import op
import sqlalchemy as sa

revision = "0008_dual_scorecard_columns"
down_revision = "0007_post_hire_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename overall_score → culture_fit_score to make the scorecard source explicit.
    # SQLite does not support RENAME COLUMN in older versions; use batch mode for portability.
    with op.batch_alter_table("interview_scores") as batch_op:
        batch_op.alter_column("overall_score", new_column_name="culture_fit_score")
        batch_op.add_column(
            sa.Column("skills_score", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            # PASS | REVIEW | FAIL — outcome from the skills model
            sa.Column("skills_outcome", sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("interview_scores") as batch_op:
        batch_op.drop_column("skills_outcome")
        batch_op.drop_column("skills_score")
        batch_op.alter_column("culture_fit_score", new_column_name="overall_score")
