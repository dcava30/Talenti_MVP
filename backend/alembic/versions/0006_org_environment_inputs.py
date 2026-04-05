"""org_environment_inputs: persist questionnaire answers and translation lineage"""

from alembic import op
import sqlalchemy as sa

revision = "0006_org_environment_inputs"
down_revision = "0005_scoring_canonical"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_environment_inputs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        # Raw questionnaire answers: JSON {question_id: answer_value}
        sa.Column("raw_answers", sa.Text(), nullable=False),
        # Translation lineage: JSON list of VariableSignal dicts
        sa.Column("signals_json", sa.Text(), nullable=True),
        # Resolved environment variables: JSON {variable: value}
        sa.Column("derived_environment", sa.Text(), nullable=False),
        # Variables that fell back to defaults: JSON list of variable names
        sa.Column("defaulted_variables", sa.Text(), nullable=True),
        # Extra fatal risk signal IDs added (e.g. from q10): JSON list
        sa.Column("extra_fatal_risks", sa.Text(), nullable=True),
        # Which user submitted the setup
        sa.Column("submitted_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_org_environment_inputs_organisation_id",
        "org_environment_inputs",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_org_environment_inputs_created_at",
        "org_environment_inputs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_org_environment_inputs_created_at", table_name="org_environment_inputs")
    op.drop_index("ix_org_environment_inputs_organisation_id", table_name="org_environment_inputs")
    op.drop_table("org_environment_inputs")
