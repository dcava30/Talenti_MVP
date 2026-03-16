"""add resume ingestion, parsed snapshots, and claimable invite state"""

from alembic import op
import sqlalchemy as sa

revision = "0004_resume_ingestion_and_claim_flow"
down_revision = "0003_blob_jobs_and_interview_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_setup_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("account_claimed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("invited_via_org", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("source_organisation_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_users_source_organisation_id_organisations",
        "users",
        "organisations",
        ["source_organisation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("users", "password_setup_required", server_default=None)
    op.alter_column("users", "invited_via_org", server_default=None)

    op.create_table(
        "parsed_profile_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("snapshot_type", sa.String(), nullable=False, server_default="resume_parse"),
        sa.Column("parser_version", sa.String(), nullable=True),
        sa.Column("source_kind", sa.String(), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("confidence_json", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "candidate_profiles",
        sa.Column("profile_prefilled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("candidate_profiles", sa.Column("profile_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("candidate_profiles", sa.Column("profile_review_status", sa.String(), nullable=True))
    op.add_column("candidate_profiles", sa.Column("prefill_source", sa.String(), nullable=True))
    op.add_column("candidate_profiles", sa.Column("parsed_snapshot_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_candidate_profiles_parsed_snapshot_id",
        "candidate_profiles",
        "parsed_profile_snapshots",
        ["parsed_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("candidate_profiles", "profile_prefilled", server_default=None)

    op.create_table(
        "resume_ingestion_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        sa.Column("job_role_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_role_id"], ["job_roles.id"]),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_ingestion_batches_job_role_id",
        "resume_ingestion_batches",
        ["job_role_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_ingestion_batches_organisation_id",
        "resume_ingestion_batches",
        ["organisation_id"],
        unique=False,
    )

    op.add_column("applications", sa.Column("source_batch_id", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("source_channel", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("profile_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column("applications", sa.Column("profile_review_status", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_applications_source_batch_id",
        "applications",
        "resume_ingestion_batches",
        ["source_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("invitations", sa.Column("candidate_email", sa.String(), nullable=True))
    op.add_column(
        "invitations",
        sa.Column("claim_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invitations",
        sa.Column("profile_completion_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("invitations", sa.Column("invitation_kind", sa.String(), nullable=True))
    op.alter_column("invitations", "claim_required", server_default=None)
    op.alter_column("invitations", "profile_completion_required", server_default=None)

    op.create_table(
        "resume_ingestion_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("batch_id", sa.String(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("parse_status", sa.String(), nullable=False),
        sa.Column("recruiter_review_status", sa.String(), nullable=False),
        sa.Column("candidate_email", sa.String(), nullable=True),
        sa.Column("candidate_name", sa.String(), nullable=True),
        sa.Column("parse_confidence_json", sa.Text(), nullable=True),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("matched_user_id", sa.String(), nullable=True),
        sa.Column("candidate_profile_id", sa.String(), nullable=True),
        sa.Column("application_id", sa.String(), nullable=True),
        sa.Column("snapshot_id", sa.String(), nullable=True),
        sa.Column("invitation_id", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["batch_id"], ["resume_ingestion_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["parsed_profile_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_ingestion_items_batch_id",
        "resume_ingestion_items",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_ingestion_items_parse_status",
        "resume_ingestion_items",
        ["parse_status"],
        unique=False,
    )
    op.create_index(
        "ix_resume_ingestion_items_recruiter_review_status",
        "resume_ingestion_items",
        ["recruiter_review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_resume_ingestion_items_recruiter_review_status", table_name="resume_ingestion_items")
    op.drop_index("ix_resume_ingestion_items_parse_status", table_name="resume_ingestion_items")
    op.drop_index("ix_resume_ingestion_items_batch_id", table_name="resume_ingestion_items")
    op.drop_table("resume_ingestion_items")

    op.drop_column("invitations", "invitation_kind")
    op.drop_column("invitations", "profile_completion_required")
    op.drop_column("invitations", "claim_required")
    op.drop_column("invitations", "candidate_email")

    op.drop_constraint("fk_applications_source_batch_id", "applications", type_="foreignkey")
    op.drop_column("applications", "profile_review_status")
    op.drop_column("applications", "profile_confirmed_at")
    op.drop_column("applications", "source_channel")
    op.drop_column("applications", "source_batch_id")

    op.drop_index("ix_resume_ingestion_batches_organisation_id", table_name="resume_ingestion_batches")
    op.drop_index("ix_resume_ingestion_batches_job_role_id", table_name="resume_ingestion_batches")
    op.drop_table("resume_ingestion_batches")

    op.drop_constraint(
        "fk_candidate_profiles_parsed_snapshot_id", "candidate_profiles", type_="foreignkey"
    )
    op.drop_column("candidate_profiles", "parsed_snapshot_id")
    op.drop_column("candidate_profiles", "prefill_source")
    op.drop_column("candidate_profiles", "profile_review_status")
    op.drop_column("candidate_profiles", "profile_confirmed_at")
    op.drop_column("candidate_profiles", "profile_prefilled")

    op.drop_table("parsed_profile_snapshots")

    op.drop_constraint(
        "fk_users_source_organisation_id_organisations", "users", type_="foreignkey"
    )
    op.drop_column("users", "source_organisation_id")
    op.drop_column("users", "invited_via_org")
    op.drop_column("users", "account_claimed_at")
    op.drop_column("users", "password_setup_required")
