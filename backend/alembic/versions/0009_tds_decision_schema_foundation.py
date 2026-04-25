"""tds: add additive decision-first persistence foundation tables"""

from alembic import op
import sqlalchemy as sa

revision = "0009_tds_decision_schema_base"
down_revision = "0008_dual_scorecard_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_outcomes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("interview_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        sa.Column("org_environment_input_id", sa.String(), nullable=True),
        sa.Column("decision_state", sa.String(), nullable=False),
        sa.Column("decision_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("confidence_gate_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("integrity_status", sa.String(), nullable=False),
        sa.Column("environment_profile_json", sa.Text(), nullable=False),
        sa.Column("critical_dimensions_json", sa.Text(), nullable=False),
        sa.Column("minimum_dimensions_json", sa.Text(), nullable=False),
        sa.Column("priority_dimensions_json", sa.Text(), nullable=False),
        sa.Column("evidence_gaps_json", sa.Text(), nullable=False),
        sa.Column("invalid_signals_json", sa.Text(), nullable=False),
        sa.Column("conflict_flags_json", sa.Text(), nullable=False),
        sa.Column("execution_floor_result_json", sa.Text(), nullable=False),
        sa.Column("trade_off_statement", sa.Text(), nullable=True),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("audit_trace_json", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"]),
        sa.ForeignKeyConstraint(["org_environment_input_id"], ["org_environment_inputs.id"]),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["job_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_outcomes_interview_id", "decision_outcomes", ["interview_id"], unique=False)
    op.create_index("ix_decision_outcomes_candidate_id", "decision_outcomes", ["candidate_id"], unique=False)
    op.create_index("ix_decision_outcomes_role_id", "decision_outcomes", ["role_id"], unique=False)
    op.create_index("ix_decision_outcomes_organisation_id", "decision_outcomes", ["organisation_id"], unique=False)
    op.create_index("ix_decision_outcomes_created_at", "decision_outcomes", ["created_at"], unique=False)
    op.create_index("ix_decision_outcomes_decision_state", "decision_outcomes", ["decision_state"], unique=False)

    op.create_table(
        "decision_dimension_evaluations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("dimension", sa.String(), nullable=False),
        sa.Column("score_internal", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("required_level", sa.String(), nullable=True),
        sa.Column("threshold_status", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("evidence_summary_json", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_outcomes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_dimension_evaluations_decision_id",
        "decision_dimension_evaluations",
        ["decision_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_dimension_evaluations_dimension",
        "decision_dimension_evaluations",
        ["dimension"],
        unique=False,
    )
    op.create_index(
        "ix_decision_dimension_evaluations_outcome",
        "decision_dimension_evaluations",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        "ix_decision_dimension_evaluations_confidence",
        "decision_dimension_evaluations",
        ["confidence"],
        unique=False,
    )

    op.create_table(
        "decision_signal_evidence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("dimension", sa.String(), nullable=True),
        sa.Column("signal_code", sa.String(), nullable=True),
        sa.Column("signal_status", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_reference_json", sa.Text(), nullable=True),
        sa.Column("raw_excerpt_json", sa.Text(), nullable=True),
        sa.Column("invalid_reason_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_outcomes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_signal_evidence_decision_id", "decision_signal_evidence", ["decision_id"], unique=False)
    op.create_index("ix_decision_signal_evidence_dimension", "decision_signal_evidence", ["dimension"], unique=False)
    op.create_index(
        "ix_decision_signal_evidence_signal_status",
        "decision_signal_evidence",
        ["signal_status"],
        unique=False,
    )

    op.create_table(
        "decision_risk_flags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("risk_code", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("source_dimension", sa.String(), nullable=True),
        sa.Column("trigger_rule", sa.String(), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_outcomes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_risk_flags_decision_id", "decision_risk_flags", ["decision_id"], unique=False)
    op.create_index("ix_decision_risk_flags_risk_code", "decision_risk_flags", ["risk_code"], unique=False)
    op.create_index(
        "ix_decision_risk_flags_source_dimension",
        "decision_risk_flags",
        ["source_dimension"],
        unique=False,
    )
    op.create_index("ix_decision_risk_flags_severity", "decision_risk_flags", ["severity"], unique=False)

    op.create_table(
        "decision_audit_trail",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_at", sa.DateTime(), nullable=False),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("rule_version", sa.String(), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=True),
        sa.Column("event_payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_outcomes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_audit_trail_decision_id", "decision_audit_trail", ["decision_id"], unique=False)
    op.create_index("ix_decision_audit_trail_event_type", "decision_audit_trail", ["event_type"], unique=False)
    op.create_index("ix_decision_audit_trail_event_at", "decision_audit_trail", ["event_at"], unique=False)
    op.create_index("ix_decision_audit_trail_actor_user_id", "decision_audit_trail", ["actor_user_id"], unique=False)

    op.create_table(
        "decision_policy_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("policy_definition_json", sa.Text(), nullable=False),
        sa.Column("critical_dimensions_json", sa.Text(), nullable=False),
        sa.Column("minimum_dimensions_json", sa.Text(), nullable=False),
        sa.Column("priority_dimensions_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["job_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_policy_versions_organisation_id",
        "decision_policy_versions",
        ["organisation_id"],
        unique=False,
    )
    op.create_index("ix_decision_policy_versions_role_id", "decision_policy_versions", ["role_id"], unique=False)
    op.create_index(
        "ix_decision_policy_versions_policy_version",
        "decision_policy_versions",
        ["policy_version"],
        unique=False,
    )
    op.create_index("ix_decision_policy_versions_status", "decision_policy_versions", ["status"], unique=False)
    op.create_index(
        "ix_decision_policy_versions_effective_from",
        "decision_policy_versions",
        ["effective_from"],
        unique=False,
    )

    op.create_table(
        "human_review_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("review_outcome", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(), nullable=False),
        sa.Column("notes_json", sa.Text(), nullable=True),
        sa.Column("display_delta_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_outcomes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_human_review_actions_decision_id", "human_review_actions", ["decision_id"], unique=False)
    op.create_index("ix_human_review_actions_reviewed_by", "human_review_actions", ["reviewed_by"], unique=False)
    op.create_index("ix_human_review_actions_action_type", "human_review_actions", ["action_type"], unique=False)
    op.create_index("ix_human_review_actions_created_at", "human_review_actions", ["created_at"], unique=False)

    op.create_table(
        "skills_assessment_summaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("interview_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        sa.Column("observed_competencies_json", sa.Text(), nullable=True),
        sa.Column("competency_coverage_json", sa.Text(), nullable=True),
        sa.Column("skill_gaps_json", sa.Text(), nullable=True),
        sa.Column("evidence_strength", sa.String(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("source_references_json", sa.Text(), nullable=True),
        sa.Column("human_readable_summary", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("excluded_from_tds_decisioning", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"]),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["job_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_skills_assessment_summaries_interview_id",
        "skills_assessment_summaries",
        ["interview_id"],
        unique=False,
    )
    op.create_index(
        "ix_skills_assessment_summaries_candidate_id",
        "skills_assessment_summaries",
        ["candidate_id"],
        unique=False,
    )
    op.create_index("ix_skills_assessment_summaries_role_id", "skills_assessment_summaries", ["role_id"], unique=False)
    op.create_index(
        "ix_skills_assessment_summaries_organisation_id",
        "skills_assessment_summaries",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_skills_assessment_summaries_created_at",
        "skills_assessment_summaries",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_skills_assessment_summaries_requires_human_review",
        "skills_assessment_summaries",
        ["requires_human_review"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_skills_assessment_summaries_requires_human_review",
        table_name="skills_assessment_summaries",
    )
    op.drop_index("ix_skills_assessment_summaries_created_at", table_name="skills_assessment_summaries")
    op.drop_index("ix_skills_assessment_summaries_organisation_id", table_name="skills_assessment_summaries")
    op.drop_index("ix_skills_assessment_summaries_role_id", table_name="skills_assessment_summaries")
    op.drop_index("ix_skills_assessment_summaries_candidate_id", table_name="skills_assessment_summaries")
    op.drop_index("ix_skills_assessment_summaries_interview_id", table_name="skills_assessment_summaries")
    op.drop_table("skills_assessment_summaries")

    op.drop_index("ix_human_review_actions_created_at", table_name="human_review_actions")
    op.drop_index("ix_human_review_actions_action_type", table_name="human_review_actions")
    op.drop_index("ix_human_review_actions_reviewed_by", table_name="human_review_actions")
    op.drop_index("ix_human_review_actions_decision_id", table_name="human_review_actions")
    op.drop_table("human_review_actions")

    op.drop_index("ix_decision_policy_versions_effective_from", table_name="decision_policy_versions")
    op.drop_index("ix_decision_policy_versions_status", table_name="decision_policy_versions")
    op.drop_index("ix_decision_policy_versions_policy_version", table_name="decision_policy_versions")
    op.drop_index("ix_decision_policy_versions_role_id", table_name="decision_policy_versions")
    op.drop_index("ix_decision_policy_versions_organisation_id", table_name="decision_policy_versions")
    op.drop_table("decision_policy_versions")

    op.drop_index("ix_decision_audit_trail_actor_user_id", table_name="decision_audit_trail")
    op.drop_index("ix_decision_audit_trail_event_at", table_name="decision_audit_trail")
    op.drop_index("ix_decision_audit_trail_event_type", table_name="decision_audit_trail")
    op.drop_index("ix_decision_audit_trail_decision_id", table_name="decision_audit_trail")
    op.drop_table("decision_audit_trail")

    op.drop_index("ix_decision_risk_flags_severity", table_name="decision_risk_flags")
    op.drop_index("ix_decision_risk_flags_source_dimension", table_name="decision_risk_flags")
    op.drop_index("ix_decision_risk_flags_risk_code", table_name="decision_risk_flags")
    op.drop_index("ix_decision_risk_flags_decision_id", table_name="decision_risk_flags")
    op.drop_table("decision_risk_flags")

    op.drop_index("ix_decision_signal_evidence_signal_status", table_name="decision_signal_evidence")
    op.drop_index("ix_decision_signal_evidence_dimension", table_name="decision_signal_evidence")
    op.drop_index("ix_decision_signal_evidence_decision_id", table_name="decision_signal_evidence")
    op.drop_table("decision_signal_evidence")

    op.drop_index(
        "ix_decision_dimension_evaluations_confidence",
        table_name="decision_dimension_evaluations",
    )
    op.drop_index("ix_decision_dimension_evaluations_outcome", table_name="decision_dimension_evaluations")
    op.drop_index("ix_decision_dimension_evaluations_dimension", table_name="decision_dimension_evaluations")
    op.drop_index("ix_decision_dimension_evaluations_decision_id", table_name="decision_dimension_evaluations")
    op.drop_table("decision_dimension_evaluations")

    op.drop_index("ix_decision_outcomes_decision_state", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_created_at", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_organisation_id", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_role_id", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_candidate_id", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_interview_id", table_name="decision_outcomes")
    op.drop_table("decision_outcomes")
