"""add blob-first file linkage and background job tables"""

from alembic import op
import sqlalchemy as sa

revision = "0003_blob_jobs_and_interview_lifecycle"
down_revision = "0002_recording_lifecycle_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("files", sa.Column("purpose", sa.String(), nullable=False, server_default="general"))
    op.alter_column("files", "purpose", server_default=None)

    op.add_column("candidate_profiles", sa.Column("cv_file_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_candidate_profiles_cv_file_id_files",
        "candidate_profiles",
        "files",
        ["cv_file_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("interviews", sa.Column("anti_cheat_signals", sa.Text(), nullable=True))
    op.add_column("interviews", sa.Column("session_metadata", sa.Text(), nullable=True))

    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_background_jobs_job_type", "background_jobs", ["job_type"], unique=False)
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"], unique=False)
    op.create_index("ix_background_jobs_available_at", "background_jobs", ["available_at"], unique=False)
    op.create_index("ix_background_jobs_correlation_id", "background_jobs", ["correlation_id"], unique=False)

    op.create_table(
        "domain_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("aggregate_type", sa.String(), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_domain_events_event_type", "domain_events", ["event_type"], unique=False)
    op.create_index("ix_domain_events_aggregate_type", "domain_events", ["aggregate_type"], unique=False)
    op.create_index("ix_domain_events_aggregate_id", "domain_events", ["aggregate_id"], unique=False)
    op.create_index("ix_domain_events_correlation_id", "domain_events", ["correlation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_domain_events_correlation_id", table_name="domain_events")
    op.drop_index("ix_domain_events_aggregate_id", table_name="domain_events")
    op.drop_index("ix_domain_events_aggregate_type", table_name="domain_events")
    op.drop_index("ix_domain_events_event_type", table_name="domain_events")
    op.drop_table("domain_events")

    op.drop_index("ix_background_jobs_correlation_id", table_name="background_jobs")
    op.drop_index("ix_background_jobs_available_at", table_name="background_jobs")
    op.drop_index("ix_background_jobs_status", table_name="background_jobs")
    op.drop_index("ix_background_jobs_job_type", table_name="background_jobs")
    op.drop_table("background_jobs")

    op.drop_column("interviews", "session_metadata")
    op.drop_column("interviews", "anti_cheat_signals")

    op.drop_constraint("fk_candidate_profiles_cv_file_id_files", "candidate_profiles", type_="foreignkey")
    op.drop_column("candidate_profiles", "cv_file_id")

    op.drop_column("files", "purpose")
