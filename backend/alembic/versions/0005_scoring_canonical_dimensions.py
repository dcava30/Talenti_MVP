"""scoring: canonical dimensions, alignment, risk, confidence, human override, env snapshot"""

from alembic import op
import sqlalchemy as sa

revision = "0005_scoring_canonical"
down_revision = "0004_resume_claim_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── interview_scores ──────────────────────────────────────────────────────
    # overall_alignment: strong_fit | mixed_fit | weak_fit
    op.add_column(
        "interview_scores",
        sa.Column("overall_alignment", sa.String(), nullable=True),
    )
    # overall_risk_level: low | medium | high
    op.add_column(
        "interview_scores",
        sa.Column("overall_risk_level", sa.String(), nullable=True),
    )
    # recommendation enum: proceed | caution | reject
    # (existing `recommendation` column is already present as String — no-op for column add,
    #  but we normalise it to the canonical values via application logic)

    # human_override: manual recruiter decision that overrides recommendation
    op.add_column(
        "interview_scores",
        sa.Column("human_override", sa.String(), nullable=True),
    )
    op.add_column(
        "interview_scores",
        sa.Column("human_override_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "interview_scores",
        sa.Column("human_override_by", sa.String(), nullable=True),
    )
    op.add_column(
        "interview_scores",
        sa.Column("human_override_at", sa.DateTime(), nullable=True),
    )
    # env_snapshot: JSON blob of the OperatingEnvironment used at scoring time
    op.add_column(
        "interview_scores",
        sa.Column("env_snapshot", sa.Text(), nullable=True),
    )
    # dimension_outcomes: JSON blob {dim: {outcome, required_pass, required_watch, gap}}
    op.add_column(
        "interview_scores",
        sa.Column("dimension_outcomes", sa.Text(), nullable=True),
    )
    # model_version: which scorer version produced this record
    op.add_column(
        "interview_scores",
        sa.Column("model_version", sa.String(), nullable=True),
    )
    # service_scores: raw JSON blobs from each model service, pre-merge
    op.add_column(
        "interview_scores",
        sa.Column("service1_raw", sa.Text(), nullable=True),
    )
    op.add_column(
        "interview_scores",
        sa.Column("service2_raw", sa.Text(), nullable=True),
    )

    # ── score_dimensions ─────────────────────────────────────────────────────
    # confidence: evidence-derived, independent of score
    op.add_column(
        "score_dimensions",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    # outcome: pass | watch | risk  (candidate-vs-environment match result)
    op.add_column(
        "score_dimensions",
        sa.Column("outcome", sa.String(), nullable=True),
    )
    # required_pass / required_watch: env-derived thresholds at scoring time
    op.add_column(
        "score_dimensions",
        sa.Column("required_pass", sa.Integer(), nullable=True),
    )
    op.add_column(
        "score_dimensions",
        sa.Column("required_watch", sa.Integer(), nullable=True),
    )
    # gap: score − required_pass (negative = shortfall)
    op.add_column(
        "score_dimensions",
        sa.Column("gap", sa.Integer(), nullable=True),
    )
    # matched_signals: JSON array of matched keyword labels
    op.add_column(
        "score_dimensions",
        sa.Column("matched_signals", sa.Text(), nullable=True),
    )
    # source: which model service contributed this dimension score
    op.add_column(
        "score_dimensions",
        sa.Column("source", sa.String(), nullable=True),
    )

    # ── index for fast dimension lookups ─────────────────────────────────────
    op.create_index(
        "ix_score_dimensions_interview_id_name",
        "score_dimensions",
        ["interview_id", "name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_score_dimensions_interview_id_name", table_name="score_dimensions")

    op.drop_column("score_dimensions", "source")
    op.drop_column("score_dimensions", "matched_signals")
    op.drop_column("score_dimensions", "gap")
    op.drop_column("score_dimensions", "required_watch")
    op.drop_column("score_dimensions", "required_pass")
    op.drop_column("score_dimensions", "outcome")
    op.drop_column("score_dimensions", "confidence")

    op.drop_column("interview_scores", "service2_raw")
    op.drop_column("interview_scores", "service1_raw")
    op.drop_column("interview_scores", "model_version")
    op.drop_column("interview_scores", "dimension_outcomes")
    op.drop_column("interview_scores", "env_snapshot")
    op.drop_column("interview_scores", "human_override_at")
    op.drop_column("interview_scores", "human_override_by")
    op.drop_column("interview_scores", "human_override_reason")
    op.drop_column("interview_scores", "human_override")
    op.drop_column("interview_scores", "overall_risk_level")
    op.drop_column("interview_scores", "overall_alignment")
