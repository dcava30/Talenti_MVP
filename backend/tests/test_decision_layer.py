import importlib
import sys

import pytest
from conftest import backend_root, clear_app_modules, prepare_test_environment
from pydantic import ValidationError


CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


def _load_modules():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    clear_app_modules()

    import app.schemas.decisioning as decisioning
    import app.services.decision_layer as decision_layer
    import app.services.interview_scoring as interview_scoring

    importlib.reload(decisioning)
    importlib.reload(decision_layer)
    importlib.reload(interview_scoring)
    return decisioning, decision_layer, interview_scoring


def _dimension(
    score: int = 1,
    confidence: str = "HIGH",
    *,
    valid_signals: list[str] | None = None,
    invalid_signals: list[str] | None = None,
    conflict_flags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "score_internal": score,
        "confidence": confidence,
        "evidence_summary": "Observed behavioural evidence.",
        "rationale": "Deterministic behavioural rationale.",
        "valid_signals": list(["repeatable_signal"] if valid_signals is None else valid_signals),
        "invalid_signals": list([] if invalid_signals is None else invalid_signals),
        "conflict_flags": list([] if conflict_flags is None else conflict_flags),
    }


def _base_payload(
    *,
    dimensions: dict[str, dict[str, object] | None] | None = None,
    critical_dimensions: list[str] | None = None,
    minimum_dimensions: list[str] | None = None,
    priority_dimensions: list[str] | None = None,
) -> dict[str, object]:
    evidence = {
        dimension: _dimension()
        for dimension in CANONICAL_DIMENSIONS
    }
    for dimension, override in (dimensions or {}).items():
        if override is None:
            evidence.pop(dimension, None)
            continue
        merged = dict(evidence.get(dimension, _dimension()))
        merged.update(override)
        evidence[dimension] = merged

    behavioural_dimension_evidence = [
        {"dimension": dimension, **evidence[dimension]}
        for dimension in CANONICAL_DIMENSIONS
        if dimension in evidence
    ]

    return {
        "interview_id": "int-123",
        "candidate_id": "cand-123",
        "role_id": "role-123",
        "organisation_id": "org-123",
        "environment_profile": {
            "control_vs_autonomy": "full_ownership",
            "outcome_vs_process": "results_first",
        },
        "environment_confidence": "HIGH",
        "behavioural_dimension_evidence": behavioural_dimension_evidence,
        "critical_dimensions": critical_dimensions if critical_dimensions is not None else ["ownership", "execution"],
        "minimum_dimensions": minimum_dimensions if minimum_dimensions is not None else list(CANONICAL_DIMENSIONS),
        "priority_dimensions": priority_dimensions if priority_dimensions is not None else ["challenge"],
        "rule_version": "tds-phase2-shadow-v1",
        "policy_version": "mvp1-behaviour-decides-v1",
    }


def _evaluate(payload: dict[str, object]):
    _, decision_layer, _ = _load_modules()
    return decision_layer.evaluate_behavioural_decision(payload)


def _risk_codes(result) -> list[str]:
    return [risk.risk_code for risk in result.risk_stack]


def _find_risk(result, risk_code: str, source_dimension: str | None = None):
    for risk in result.risk_stack:
        if risk.risk_code != risk_code:
            continue
        if source_dimension is not None and risk.source_dimension != source_dimension:
            continue
        return risk
    return None


def test_missing_critical_dimension_returns_insufficient_evidence() -> None:
    result = _evaluate(_base_payload(dimensions={"ownership": None}))

    assert result.decision_state.value == "INSUFFICIENT_EVIDENCE"
    assert result.confidence_gate_passed is False
    assert result.decision_valid is False
    assert result.evidence_gaps == ["ownership"]
    assert result.integrity_status.value == "INVALID"


def test_critical_dimension_with_no_valid_signals_returns_insufficient_evidence() -> None:
    result = _evaluate(
        _base_payload(dimensions={"ownership": _dimension(valid_signals=[])})
    )

    assert result.decision_state.value == "INSUFFICIENT_EVIDENCE"
    assert result.evidence_gaps == ["ownership"]


def test_critical_dimension_with_low_confidence_fails_confidence_gate() -> None:
    result = _evaluate(
        _base_payload(dimensions={"ownership": _dimension(confidence="LOW")})
    )

    assert result.confidence_gate_passed is False
    assert result.confidence.value == "LOW"
    assert result.decision_state.value == "INSUFFICIENT_EVIDENCE"


def test_missing_non_critical_dimension_does_not_invalidate_decision() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={"feedback": None},
            minimum_dimensions=["ownership", "execution"],
            priority_dimensions=["challenge"],
        )
    )

    assert result.decision_state.value == "PROCEED"
    assert result.evidence_gaps == []


def test_all_critical_dimensions_medium_or_high_pass_confidence_gate() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "ownership": _dimension(confidence="MEDIUM"),
                "execution": _dimension(confidence="HIGH"),
            }
        )
    )

    assert result.confidence_gate_passed is True
    assert result.confidence.value == "MEDIUM"


def test_execution_floor_rejects_execution_minus_two_with_medium_confidence() -> None:
    result = _evaluate(
        _base_payload(dimensions={"execution": _dimension(score=-2, confidence="MEDIUM")})
    )

    assert result.decision_state.value == "DO_NOT_PROCEED"
    assert result.decision_valid is True
    assert result.execution_floor_result.passed is False
    assert result.execution_floor_result.trigger_rule == "execution_floor_reject"
    assert result.integrity_status.value == "AT_RISK"


def test_execution_minus_one_with_medium_confidence_caps_outcome_below_proceed() -> None:
    result = _evaluate(
        _base_payload(dimensions={"execution": _dimension(score=-1, confidence="MEDIUM")})
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"
    assert result.execution_floor_result.passed is False
    assert _find_risk(result, "execution_negative_medium_confidence", "execution") is not None


def test_execution_minus_one_with_low_confidence_does_not_independently_reject() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={"execution": _dimension(score=-1, confidence="LOW")},
            critical_dimensions=["ownership"],
            minimum_dimensions=["ownership", "execution"],
        )
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"
    assert result.execution_floor_result.trigger_rule == "execution_floor_low_confidence_uncertain"
    assert result.risk_stack == []


def test_missing_critical_execution_returns_insufficient_evidence() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={"execution": None},
            critical_dimensions=["ownership", "execution"],
        )
    )

    assert result.decision_state.value == "INSUFFICIENT_EVIDENCE"
    assert "execution" in result.evidence_gaps


def test_critical_dimension_minus_two_with_medium_confidence_returns_do_not_proceed() -> None:
    result = _evaluate(
        _base_payload(dimensions={"ownership": _dimension(score=-2, confidence="MEDIUM")})
    )

    assert result.decision_state.value == "DO_NOT_PROCEED"
    assert _find_risk(result, "critical_dimension_failure", "ownership") is not None


def test_critical_dimension_minus_one_with_medium_confidence_cannot_proceed() -> None:
    result = _evaluate(
        _base_payload(dimensions={"ownership": _dimension(score=-1, confidence="MEDIUM")})
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"
    assert result.decision_state.value != "PROCEED"


def test_minimum_dimension_minus_one_with_medium_confidence_adds_risk() -> None:
    result = _evaluate(
        _base_payload(dimensions={"feedback": _dimension(score=-1, confidence="MEDIUM")})
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"
    assert _find_risk(result, "minimum_dimension_risk", "feedback") is not None


def test_multiple_minimum_failures_follow_risk_stack_rules() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "challenge": _dimension(score=-1, confidence="MEDIUM"),
                "ambiguity": _dimension(score=-1, confidence="HIGH"),
            },
            priority_dimensions=[],
        )
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"
    assert len(result.risk_stack) == 2


def test_zero_risks_with_all_requirements_met_returns_proceed() -> None:
    result = _evaluate(_base_payload())

    assert result.decision_state.value == "PROCEED"
    assert result.risk_stack == []
    assert result.integrity_status.value == "CLEAN"


def test_three_risks_returns_do_not_proceed() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "challenge": _dimension(score=-1, confidence="MEDIUM"),
                "ambiguity": _dimension(score=-1, confidence="MEDIUM"),
                "feedback": _dimension(score=-1, confidence="HIGH"),
            },
            priority_dimensions=[],
        )
    )

    assert result.decision_state.value == "DO_NOT_PROCEED"
    assert len(result.risk_stack) == 3


def test_low_confidence_negative_does_not_count_as_risk() -> None:
    result = _evaluate(
        _base_payload(dimensions={"feedback": _dimension(score=-1, confidence="LOW")})
    )

    assert result.decision_state.value == "PROCEED"
    assert result.risk_stack == []


def test_positive_priority_can_upgrade_borderline_case_when_no_blockers_exist() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "ownership": _dimension(score=0, confidence="MEDIUM"),
                "challenge": _dimension(score=1, confidence="HIGH"),
            }
        )
    )

    assert result.decision_state.value == "PROCEED"
    assert any(entry.details.get("status") == "positive_priority_upgrade" for entry in result.audit_trace if entry.code == "priority_dimension_result")


def test_positive_priority_cannot_override_critical_failure() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "ownership": _dimension(score=-1, confidence="MEDIUM"),
                "challenge": _dimension(score=1, confidence="HIGH"),
            }
        )
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"


def test_positive_priority_cannot_override_execution_floor() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "execution": _dimension(score=-1, confidence="MEDIUM"),
                "challenge": _dimension(score=1, confidence="HIGH"),
            }
        )
    )

    assert result.decision_state.value == "PROCEED_WITH_CONDITIONS"


def test_negative_priority_degrades_borderline_decision() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "feedback": _dimension(score=-1, confidence="MEDIUM"),
                "challenge": _dimension(score=-1, confidence="MEDIUM"),
            }
        )
    )

    assert result.decision_state.value == "DO_NOT_PROCEED"
    assert _find_risk(result, "priority_dimension_negative", "challenge") is not None


def test_conflict_but_valid_case_is_mixed() -> None:
    result = _evaluate(
        _base_payload(dimensions={"feedback": _dimension(conflict_flags=["feedback_conflict"])})
    )

    assert result.decision_state.value == "PROCEED"
    assert result.integrity_status.value == "MIXED"


def test_invalid_signal_dominance_returns_invalid_integrity() -> None:
    result = _evaluate(
        _base_payload(
            dimensions={
                "ownership": _dimension(
                    confidence="MEDIUM",
                    valid_signals=["single_signal"],
                    invalid_signals=["bad_a", "bad_b"],
                ),
                "execution": _dimension(
                    confidence="MEDIUM",
                    valid_signals=["single_signal"],
                    invalid_signals=["bad_c", "bad_d"],
                ),
            }
        )
    )

    assert result.decision_state.value == "INSUFFICIENT_EVIDENCE"
    assert result.integrity_status.value == "INVALID"


def test_skills_fields_are_rejected_from_direct_decision_layer_payloads() -> None:
    _, decision_layer, _ = _load_modules()
    payload = _base_payload()
    payload["skills_score"] = 99
    payload["skills_outcome"] = "PASS"
    payload["review"] = "REVIEW"
    payload["skills_assessment_summary"] = {"outcome": "FAIL"}

    with pytest.raises(ValueError, match="behavioural evidence only"):
        decision_layer.evaluate_behavioural_decision(payload)


def test_fake_skills_fields_do_not_affect_decision_state_risk_stack_or_rationale_via_dark_builder() -> None:
    _, decision_layer, interview_scoring = _load_modules()
    clean_context = _base_payload()
    dirty_context = {
        **_base_payload(),
        "skills_score": 1,
        "skills_outcome": "FAIL",
        "overall_score": 0,
        "review": "REVIEW",
        "pass": "PASS",
        "fail": "FAIL",
        "must_haves_passed": ["python"],
        "must_haves_failed": ["sql"],
        "gaps": ["forecasting"],
        "skills_assessment_summary": {"summary": "Ignore me"},
        "skills_fit": {"outcome": "PASS", "gaps": ["ignore me too"]},
        "service2_raw": {"skills_outcome": "PASS"},
    }

    clean_input = interview_scoring.build_behavioural_decision_input_from_scoring_context(
        clean_context
    )
    dirty_input = interview_scoring.build_behavioural_decision_input_from_scoring_context(
        dirty_context
    )

    clean_result = decision_layer.evaluate_behavioural_decision(clean_input)
    dirty_result = decision_layer.evaluate_behavioural_decision(dirty_input)

    assert dirty_input.model_dump(mode="json") == clean_input.model_dump(mode="json")
    assert "skills_score" not in dirty_input.model_dump(mode="json")
    assert "skills_outcome" not in dirty_input.model_dump(mode="json")
    assert "must_haves_passed" not in dirty_input.model_dump(mode="json")
    assert "gaps" not in dirty_input.model_dump(mode="json")
    assert dirty_result.decision_state == clean_result.decision_state
    assert dirty_result.risk_stack == clean_result.risk_stack
    assert dirty_result.rationale == clean_result.rationale


def test_behavioural_decision_input_validation_rejects_nested_skills_fields() -> None:
    decisioning, _, _ = _load_modules()
    payload = _base_payload()
    payload["environment_profile"]["skills_summary"] = "contaminated"

    with pytest.raises(ValidationError, match="skills-derived fields"):
        decisioning.BehaviouralDecisionInput.model_validate(payload)


def test_output_is_deterministic_for_identical_inputs() -> None:
    payload = _base_payload(
        dimensions={
            "feedback": _dimension(score=-1, confidence="MEDIUM"),
            "challenge": _dimension(score=1, confidence="HIGH"),
        }
    )

    first = _evaluate(payload)
    second = _evaluate(payload)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_audit_trace_marks_rule_enforcement_as_active_and_not_pending() -> None:
    result = _evaluate(_base_payload())

    audit_codes = [entry.code for entry in result.audit_trace]
    assert "tds_rule_slice_1_enforced" in audit_codes
    assert "full_tds_rule_enforcement_pending" not in audit_codes
    assert {
        "evidence_sufficiency_result",
        "confidence_gate_result",
        "execution_floor_result",
        "critical_dimension_result",
        "minimum_dimension_result",
        "priority_dimension_result",
        "risk_stack_result",
        "final_resolution_path",
    }.issubset(set(audit_codes))
