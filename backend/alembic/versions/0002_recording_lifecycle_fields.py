"""add recording lifecycle fields to interviews"""

from alembic import op
import sqlalchemy as sa

revision = "0002_recording_lifecycle_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("interviews", sa.Column("call_connection_id", sa.String(), nullable=True))
    op.add_column("interviews", sa.Column("server_call_id", sa.String(), nullable=True))
    op.add_column("interviews", sa.Column("recording_id", sa.String(), nullable=True))
    op.add_column(
        "interviews",
        sa.Column("recording_started", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "interviews",
        sa.Column("recording_processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("interviews", sa.Column("recording_status", sa.String(), nullable=True))
    op.add_column("interviews", sa.Column("recording_error", sa.Text(), nullable=True))
    op.add_column("interviews", sa.Column("recording_started_at", sa.DateTime(), nullable=True))
    op.add_column("interviews", sa.Column("recording_stopped_at", sa.DateTime(), nullable=True))
    op.add_column("interviews", sa.Column("recording_processed_at", sa.DateTime(), nullable=True))

    op.alter_column("interviews", "recording_started", server_default=None)
    op.alter_column("interviews", "recording_processed", server_default=None)


def downgrade() -> None:
    op.drop_column("interviews", "recording_processed_at")
    op.drop_column("interviews", "recording_stopped_at")
    op.drop_column("interviews", "recording_started_at")
    op.drop_column("interviews", "recording_error")
    op.drop_column("interviews", "recording_status")
    op.drop_column("interviews", "recording_processed")
    op.drop_column("interviews", "recording_started")
    op.drop_column("interviews", "recording_id")
    op.drop_column("interviews", "server_call_id")
    op.drop_column("interviews", "call_connection_id")
