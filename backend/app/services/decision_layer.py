from __future__ import annotations

from typing import Any

from app.schemas.decisioning import (
    CANONICAL_BEHAVIOURAL_DIMENSIONS,
    BehaviouralDecisionInput,
    BehaviouralDecisionOutput,
    ConfidenceBand,
    DecisionAuditEntry,
    DecisionDimensionEvaluation,
    DecisionRiskItem,
    DecisionState,
    DimensionEvaluationStatus,
    ExecutionFloorResult,
    IntegrityState,
    RiskSeverity,
    assert_behavioural_only_payload,
)

DECISION_LAYER_RULE_VERSION = "tds-phase2-shadow-v1"
DECISION_LAYER_POLICY_VERSION = "mvp1-behaviour-decides-v1"
RULE_ENFORCEMENT_ACTIVE_MARKER = "tds_rule_slice_1_enforced"

_CONFIDENCE_ORDER = {
    ConfidenceBand.LOW: 0,
    ConfidenceBand.MEDIUM: 1,
    ConfidenceBand.HIGH: 2,
}
_MINIMUM_DIMENSION_GAP_THRESHOLD = 2


def evaluate_behavioural_decision(
    payload: BehaviouralDecisionInput | dict[str, Any],
) -> BehaviouralDecisionOutput:
    decision_input = _coerce_decision_input(payload)
    critical_dimensions = _canonicalise_dimensions(decision_input.critical_dimensions)
    minimum_dimensions = _canonicalise_dimensions(decision_input.minimum_dimensions)
    priority_dimensions = _canonicalise_dimensions(decision_input.priority_dimensions)
    minimum_only_dimensions = [dim for dim in minimum_dimensions if dim not in critical_dimensions]
    evidence_by_dimension = {
        evidence.dimension: evidence for evidence in decision_input.behavioural_dimension_evidence
    }

    dimension_contexts = _build_dimension_contexts(
        evidence_by_dimension=evidence_by_dimension,
        critical_dimensions=critical_dimensions,
        minimum_dimensions=minimum_dimensions,
        priority_dimensions=priority_dimensions,
    )
    dimension_evaluations = [
        context["evaluation"] for context in dimension_contexts if context["evaluation"] is not None
    ]
    invalid_signals = _flatten_signal_list(
        [context["invalid_signals"] for context in dimension_contexts]
    )
    conflict_flags = _flatten_signal_list(
        [context["conflict_flags"] for context in dimension_contexts]
    )

    evidence_result = _evaluate_evidence_sufficiency(
        dimension_contexts=dimension_contexts,
        critical_dimensions=critical_dimensions,
        minimum_only_dimensions=minimum_only_dimensions,
    )
    invalid_signal_dominance = _has_invalid_signal_dominance(
        dimension_contexts=dimension_contexts,
        required_dimensions=_canonicalise_dimensions(critical_dimensions + minimum_dimensions),
    )
    confidence_gate_passed = _evaluate_confidence_gate(
        critical_dimensions=critical_dimensions,
        evidence_result=evidence_result,
        invalid_signal_dominance=invalid_signal_dominance,
    )
    confidence = _derive_confidence(
        dimension_contexts=dimension_contexts,
        critical_dimensions=critical_dimensions,
        evidence_result=evidence_result,
        confidence_gate_passed=confidence_gate_passed,
        invalid_signal_dominance=invalid_signal_dominance,
    )

    execution_floor_result = _evaluate_execution_floor(
        evidence_by_dimension=evidence_by_dimension,
        critical_dimensions=critical_dimensions,
    )
    critical_result = _evaluate_critical_dimensions(
        dimension_contexts=dimension_contexts,
        critical_dimensions=critical_dimensions,
    )
    minimum_result = _evaluate_minimum_dimensions(
        dimension_contexts=dimension_contexts,
        minimum_only_dimensions=minimum_only_dimensions,
    )

    risk_stack = _build_base_risk_stack(
        evidence_by_dimension=evidence_by_dimension,
        critical_dimensions=critical_dimensions,
        minimum_only_dimensions=minimum_only_dimensions,
    )

    final_resolution_path: list[str] = []
    priority_result = {
        "status": "not_applied",
        "positive_dimensions": [],
        "negative_dimensions": [],
    }

    if not confidence_gate_passed or invalid_signal_dominance:
        decision_state = DecisionState.INSUFFICIENT_EVIDENCE
        final_resolution_path.append("insufficient_evidence_precedence")
    else:
        decision_state = _resolve_pre_priority_state(
            execution_floor_result=execution_floor_result,
            critical_result=critical_result,
            risk_stack=risk_stack,
        )
        final_resolution_path.append(f"pre_priority={decision_state.value}")
        priority_result = _apply_priority_logic(
            current_state=decision_state,
            dimension_contexts=dimension_contexts,
            priority_dimensions=priority_dimensions,
            risk_stack=risk_stack,
            execution_floor_result=execution_floor_result,
            critical_result=critical_result,
        )
        decision_state = priority_result["state"]
        final_resolution_path.append(f"post_priority={decision_state.value}")
        decision_state = _apply_final_risk_stack_resolution(decision_state, risk_stack)
        final_resolution_path.append(f"post_risk_stack={decision_state.value}")

    decision_valid = decision_state is not DecisionState.INSUFFICIENT_EVIDENCE
    integrity_status = _derive_integrity_status(
        decision_valid=decision_valid,
        confidence_gate_passed=confidence_gate_passed,
        evidence_gaps=evidence_result["evidence_gaps"],
        invalid_signal_dominance=invalid_signal_dominance,
        invalid_signals=invalid_signals,
        conflict_flags=conflict_flags,
        risk_stack=risk_stack,
        execution_floor_result=execution_floor_result,
    )
    conditions = _build_conditions(
        decision_state=decision_state,
        evidence_gaps=evidence_result["evidence_gaps"],
        risk_stack=risk_stack,
    )
    rationale = _build_rationale(
        decision_state=decision_state,
        critical_result=critical_result,
        evidence_result=evidence_result,
        risk_stack=risk_stack,
        execution_floor_result=execution_floor_result,
    )
    audit_trace = _build_audit_trace(
        decision_input=decision_input,
        evidence_result=evidence_result,
        confidence_gate_passed=confidence_gate_passed,
        confidence=confidence,
        execution_floor_result=execution_floor_result,
        critical_result=critical_result,
        minimum_result=minimum_result,
        priority_result=priority_result,
        risk_stack=risk_stack,
        decision_state=decision_state,
        integrity_status=integrity_status,
        final_resolution_path=final_resolution_path,
        invalid_signal_dominance=invalid_signal_dominance,
    )

    return BehaviouralDecisionOutput(
        decision_state=decision_state,
        decision_valid=decision_valid,
        confidence=confidence,
        confidence_gate_passed=confidence_gate_passed,
        integrity_status=integrity_status,
        critical_dimensions=critical_dimensions,
        minimum_dimensions=minimum_dimensions,
        priority_dimensions=priority_dimensions,
        dimension_evaluations=dimension_evaluations,
        evidence_gaps=evidence_result["evidence_gaps"],
        invalid_signals=invalid_signals,
        conflict_flags=conflict_flags,
        risk_stack=risk_stack,
        execution_floor_result=execution_floor_result,
        trade_off_statement=_build_trade_off_statement(decision_state),
        conditions=conditions,
        rationale=rationale,
        audit_trace=audit_trace,
        rule_version=decision_input.rule_version,
        policy_version=decision_input.policy_version,
    )


def _coerce_decision_input(
    payload: BehaviouralDecisionInput | dict[str, Any],
) -> BehaviouralDecisionInput:
    assert_behavioural_only_payload(payload)
    if isinstance(payload, BehaviouralDecisionInput):
        return payload
    return BehaviouralDecisionInput.model_validate(payload)


def _build_dimension_contexts(
    *,
    evidence_by_dimension: dict[str, Any],
    critical_dimensions: list[str],
    minimum_dimensions: list[str],
    priority_dimensions: list[str],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    observed_dimensions = [dim for dim in CANONICAL_BEHAVIOURAL_DIMENSIONS if dim in evidence_by_dimension]
    scoped_dimensions = _canonicalise_dimensions(
        critical_dimensions + minimum_dimensions + priority_dimensions + observed_dimensions
    )

    for dimension in scoped_dimensions:
        evidence = evidence_by_dimension.get(dimension)
        required_level = _required_level(
            dimension=dimension,
            critical_dimensions=critical_dimensions,
            minimum_dimensions=minimum_dimensions,
            priority_dimensions=priority_dimensions,
        )
        if evidence is None:
            contexts.append(
                {
                    "dimension": dimension,
                    "evidence": None,
                    "required_level": required_level,
                    "confidence": None,
                    "score_internal": None,
                    "valid_signals": [],
                    "invalid_signals": [],
                    "conflict_flags": [],
                    "missing": True,
                    "has_valid_signals": False,
                    "invalid_signal_dominant": False,
                    "is_critical": dimension in critical_dimensions,
                    "is_minimum": dimension in minimum_dimensions,
                    "is_priority": dimension in priority_dimensions,
                    "evaluation": DecisionDimensionEvaluation(
                        dimension=dimension,
                        status=DimensionEvaluationStatus.MISSING,
                        required_level=required_level,
                        threshold_status="insufficient_evidence",
                        outcome="insufficient_evidence",
                    ),
                }
            )
            continue

        confidence = evidence.confidence
        valid_signals = list(evidence.valid_signals)
        invalid_signals = list(evidence.invalid_signals)
        conflict_flags = list(evidence.conflict_flags)
        confidence_band = confidence or ConfidenceBand.LOW
        has_valid_signals = bool(valid_signals)
        invalid_signal_dominant = len(invalid_signals) > len(valid_signals) and bool(invalid_signals)
        threshold_status, outcome = _classify_dimension_threshold(
            score_internal=evidence.score_internal,
            confidence=confidence_band,
            has_valid_signals=has_valid_signals,
            required_level=required_level,
        )
        contexts.append(
            {
                "dimension": dimension,
                "evidence": evidence,
                "required_level": required_level,
                "confidence": confidence_band,
                "score_internal": evidence.score_internal,
                "valid_signals": valid_signals,
                "invalid_signals": invalid_signals,
                "conflict_flags": conflict_flags,
                "missing": False,
                "has_valid_signals": has_valid_signals,
                "invalid_signal_dominant": invalid_signal_dominant,
                "is_critical": dimension in critical_dimensions,
                "is_minimum": dimension in minimum_dimensions,
                "is_priority": dimension in priority_dimensions,
                "evaluation": DecisionDimensionEvaluation(
                    dimension=evidence.dimension,
                    status=DimensionEvaluationStatus.PRESENT,
                    score_internal=evidence.score_internal,
                    confidence=confidence_band,
                    required_level=required_level,
                    threshold_status=threshold_status,
                    outcome=outcome,
                    evidence_summary=evidence.evidence_summary,
                    rationale=evidence.rationale,
                    valid_signals=valid_signals,
                    invalid_signals=invalid_signals,
                    conflict_flags=conflict_flags,
                ),
            }
        )

    return contexts


def _evaluate_evidence_sufficiency(
    *,
    dimension_contexts: list[dict[str, Any]],
    critical_dimensions: list[str],
    minimum_only_dimensions: list[str],
) -> dict[str, Any]:
    indexed = {context["dimension"]: context for context in dimension_contexts}
    critical_missing: list[str] = []
    critical_no_valid: list[str] = []
    critical_low_confidence: list[str] = []
    minimum_gaps: list[str] = []
    invalid_required_dimensions: list[str] = []

    for dimension in critical_dimensions:
        context = indexed.get(dimension)
        if context is None or context["missing"]:
            critical_missing.append(dimension)
            continue
        if not context["has_valid_signals"]:
            critical_no_valid.append(dimension)
        if _confidence_order(context["confidence"]) < _confidence_order(ConfidenceBand.MEDIUM):
            critical_low_confidence.append(dimension)
        if context["invalid_signal_dominant"]:
            invalid_required_dimensions.append(dimension)

    for dimension in minimum_only_dimensions:
        context = indexed.get(dimension)
        if context is None or context["missing"] or not context["has_valid_signals"]:
            minimum_gaps.append(dimension)
            continue
        if context["invalid_signal_dominant"]:
            invalid_required_dimensions.append(dimension)

    # One missing minimum dimension can still be carried as a condition, but
    # two or more missing minimum-only dimensions make the deterministic rule
    # outcome too unreliable for this MVP1 slice.
    too_many_minimum_gaps = len(minimum_gaps) >= _MINIMUM_DIMENSION_GAP_THRESHOLD
    evidence_gaps = _canonicalise_dimensions(
        critical_missing + critical_no_valid + critical_low_confidence + minimum_gaps
    )
    insufficient = bool(
        critical_missing
        or critical_no_valid
        or critical_low_confidence
        or invalid_required_dimensions
        or too_many_minimum_gaps
    )

    return {
        "critical_missing": critical_missing,
        "critical_no_valid": critical_no_valid,
        "critical_low_confidence": critical_low_confidence,
        "minimum_gaps": minimum_gaps,
        "invalid_required_dimensions": _canonicalise_dimensions(invalid_required_dimensions),
        "too_many_minimum_gaps": too_many_minimum_gaps,
        "evidence_gaps": evidence_gaps,
        "insufficient": insufficient,
    }


def _evaluate_confidence_gate(
    *,
    critical_dimensions: list[str],
    evidence_result: dict[str, Any],
    invalid_signal_dominance: bool,
) -> bool:
    if invalid_signal_dominance:
        return False
    if evidence_result["insufficient"]:
        return False
    if not critical_dimensions:
        return True
    return not evidence_result["critical_low_confidence"]


def _derive_confidence(
    *,
    dimension_contexts: list[dict[str, Any]],
    critical_dimensions: list[str],
    evidence_result: dict[str, Any],
    confidence_gate_passed: bool,
    invalid_signal_dominance: bool,
) -> ConfidenceBand:
    if not confidence_gate_passed or evidence_result["evidence_gaps"] or invalid_signal_dominance:
        return ConfidenceBand.LOW

    critical_contexts = [
        context for context in dimension_contexts if context["dimension"] in critical_dimensions
    ]
    if not critical_contexts:
        return ConfidenceBand.MEDIUM

    has_major_conflicts = any(
        context["conflict_flags"] or context["invalid_signals"] for context in critical_contexts
    )
    if all(context["confidence"] is ConfidenceBand.HIGH for context in critical_contexts) and not has_major_conflicts:
        return ConfidenceBand.HIGH
    if all(
        _confidence_order(context["confidence"]) >= _confidence_order(ConfidenceBand.MEDIUM)
        for context in critical_contexts
    ):
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _evaluate_execution_floor(
    *,
    evidence_by_dimension: dict[str, Any],
    critical_dimensions: list[str],
) -> ExecutionFloorResult:
    execution = evidence_by_dimension.get("execution")
    if execution is None:
        if "execution" in critical_dimensions:
            return ExecutionFloorResult(
                passed=False,
                reason="Execution evidence is missing and execution is marked critical.",
                trigger_rule="execution_missing_critical",
            )
        return ExecutionFloorResult(
            passed=True,
            reason="Execution floor not triggered because execution is not required.",
            trigger_rule="execution_not_required",
        )

    confidence = execution.confidence or ConfidenceBand.LOW
    if execution.score_internal <= -2 and _confidence_order(confidence) >= _confidence_order(ConfidenceBand.MEDIUM):
        return ExecutionFloorResult(
            passed=False,
            reason="Execution breached the global floor with sufficient negative behavioural evidence.",
            trigger_rule="execution_floor_reject",
        )
    if execution.score_internal == -1 and _confidence_order(confidence) >= _confidence_order(ConfidenceBand.MEDIUM):
        return ExecutionFloorResult(
            passed=False,
            reason="Execution breached the cautionary floor and caps the outcome below PROCEED.",
            trigger_rule="execution_floor_condition_cap",
        )
    if execution.score_internal < 0:
        return ExecutionFloorResult(
            passed=False,
            reason="Execution is negative but low-confidence, so it is treated as uncertainty rather than rejection.",
            trigger_rule="execution_floor_low_confidence_uncertain",
        )
    return ExecutionFloorResult(
        passed=True,
        reason="Execution did not violate the global floor.",
        trigger_rule="execution_floor_clear",
    )


def _evaluate_critical_dimensions(
    *,
    dimension_contexts: list[dict[str, Any]],
    critical_dimensions: list[str],
) -> dict[str, Any]:
    indexed = {context["dimension"]: context for context in dimension_contexts}
    hard_failures: list[str] = []
    soft_failures: list[str] = []
    borderlines: list[str] = []

    for dimension in critical_dimensions:
        context = indexed.get(dimension)
        if context is None or context["missing"] or not context["has_valid_signals"]:
            continue
        if _confidence_order(context["confidence"]) < _confidence_order(ConfidenceBand.MEDIUM):
            continue
        if context["score_internal"] <= -2:
            hard_failures.append(dimension)
        elif context["score_internal"] <= -1:
            soft_failures.append(dimension)
        elif context["score_internal"] == 0:
            borderlines.append(dimension)

    return {
        "hard_failures": hard_failures,
        "soft_failures": soft_failures,
        "borderlines": borderlines,
        "multiple_failures": len(hard_failures) + len(soft_failures) >= 2,
    }


def _evaluate_minimum_dimensions(
    *,
    dimension_contexts: list[dict[str, Any]],
    minimum_only_dimensions: list[str],
) -> dict[str, Any]:
    indexed = {context["dimension"]: context for context in dimension_contexts}
    failing_dimensions: list[str] = []

    for dimension in minimum_only_dimensions:
        context = indexed.get(dimension)
        if context is None or context["missing"] or not context["has_valid_signals"]:
            continue
        if _confidence_order(context["confidence"]) < _confidence_order(ConfidenceBand.MEDIUM):
            continue
        if context["score_internal"] <= -1:
            failing_dimensions.append(dimension)

    return {
        "failing_dimensions": failing_dimensions,
        "count": len(failing_dimensions),
    }


def _build_base_risk_stack(
    *,
    evidence_by_dimension: dict[str, Any],
    critical_dimensions: list[str],
    minimum_only_dimensions: list[str],
) -> list[DecisionRiskItem]:
    risk_stack: list[DecisionRiskItem] = []
    execution = evidence_by_dimension.get("execution")
    if execution is not None and _confidence_order(execution.confidence or ConfidenceBand.LOW) >= _confidence_order(
        ConfidenceBand.MEDIUM
    ) and execution.score_internal <= -1:
        _add_risk(
            risk_stack,
            risk_code="execution_negative_medium_confidence",
            severity=RiskSeverity.HIGH if execution.score_internal <= -2 else RiskSeverity.MEDIUM,
            source_dimension="execution",
            trigger_rule="execution_floor",
        )

    for dimension in critical_dimensions:
        if dimension == "execution":
            continue
        evidence = evidence_by_dimension.get(dimension)
        if evidence is None:
            continue
        if _confidence_order(evidence.confidence or ConfidenceBand.LOW) < _confidence_order(
            ConfidenceBand.MEDIUM
        ):
            continue
        if evidence.score_internal <= -1:
            _add_risk(
                risk_stack,
                risk_code="critical_dimension_failure",
                severity=RiskSeverity.HIGH if evidence.score_internal <= -2 else RiskSeverity.MEDIUM,
                source_dimension=dimension,
                trigger_rule="critical_dimension_threshold",
            )

    for dimension in minimum_only_dimensions:
        evidence = evidence_by_dimension.get(dimension)
        if evidence is None:
            continue
        if _confidence_order(evidence.confidence or ConfidenceBand.LOW) < _confidence_order(
            ConfidenceBand.MEDIUM
        ):
            continue
        if evidence.score_internal <= -1:
            _add_risk(
                risk_stack,
                risk_code="minimum_dimension_risk",
                severity=RiskSeverity.MEDIUM,
                source_dimension=dimension,
                trigger_rule="minimum_dimension_threshold",
            )

    return risk_stack


def _resolve_pre_priority_state(
    *,
    execution_floor_result: ExecutionFloorResult,
    critical_result: dict[str, Any],
    risk_stack: list[DecisionRiskItem],
) -> DecisionState:
    if execution_floor_result.trigger_rule == "execution_floor_reject":
        return DecisionState.DO_NOT_PROCEED
    if critical_result["hard_failures"]:
        return DecisionState.DO_NOT_PROCEED
    if critical_result["multiple_failures"]:
        return DecisionState.DO_NOT_PROCEED

    decision_state = DecisionState.PROCEED
    if (
        execution_floor_result.trigger_rule in {
            "execution_floor_condition_cap",
            "execution_floor_low_confidence_uncertain",
        }
        or critical_result["soft_failures"]
        or critical_result["borderlines"]
    ):
        decision_state = DecisionState.PROCEED_WITH_CONDITIONS

    if len(risk_stack) >= 3:
        return DecisionState.DO_NOT_PROCEED
    if risk_stack:
        return DecisionState.PROCEED_WITH_CONDITIONS
    return decision_state


def _apply_priority_logic(
    *,
    current_state: DecisionState,
    dimension_contexts: list[dict[str, Any]],
    priority_dimensions: list[str],
    risk_stack: list[DecisionRiskItem],
    execution_floor_result: ExecutionFloorResult,
    critical_result: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "status": "not_applied",
        "positive_dimensions": [],
        "negative_dimensions": [],
        "state": current_state,
    }
    if current_state is DecisionState.INSUFFICIENT_EVIDENCE:
        return result

    indexed = {context["dimension"]: context for context in dimension_contexts}
    positive_dimensions: list[str] = []
    negative_dimensions: list[str] = []
    for dimension in priority_dimensions:
        context = indexed.get(dimension)
        if context is None or context["missing"] or not context["has_valid_signals"]:
            continue
        if _confidence_order(context["confidence"]) < _confidence_order(ConfidenceBand.MEDIUM):
            continue
        if context["score_internal"] >= 1:
            positive_dimensions.append(dimension)
        elif context["score_internal"] <= -1:
            negative_dimensions.append(dimension)

    result["positive_dimensions"] = positive_dimensions
    result["negative_dimensions"] = negative_dimensions

    if negative_dimensions:
        for dimension in negative_dimensions:
            _add_risk(
                risk_stack,
                risk_code="priority_dimension_negative",
                severity=RiskSeverity.MEDIUM,
                source_dimension=dimension,
                trigger_rule="priority_dimension_negative",
            )
        if current_state is DecisionState.PROCEED:
            result["state"] = DecisionState.PROCEED_WITH_CONDITIONS
        elif current_state is DecisionState.PROCEED_WITH_CONDITIONS:
            result["state"] = DecisionState.DO_NOT_PROCEED
        result["status"] = "negative_priority_applied"
        return result

    if (
        current_state is DecisionState.PROCEED_WITH_CONDITIONS
        and positive_dimensions
        and not critical_result["hard_failures"]
        and not critical_result["soft_failures"]
        and execution_floor_result.trigger_rule not in {
            "execution_floor_reject",
            "execution_floor_condition_cap",
            "execution_floor_low_confidence_uncertain",
        }
        and len(risk_stack) < 2
    ):
        result["state"] = DecisionState.PROCEED
        result["status"] = "positive_priority_upgrade"
        return result

    if positive_dimensions:
        result["status"] = "positive_priority_blocked"
    return result


def _apply_final_risk_stack_resolution(
    current_state: DecisionState,
    risk_stack: list[DecisionRiskItem],
) -> DecisionState:
    if current_state is DecisionState.INSUFFICIENT_EVIDENCE:
        return current_state
    if len(risk_stack) >= 3:
        return DecisionState.DO_NOT_PROCEED
    if risk_stack and current_state is DecisionState.PROCEED:
        return DecisionState.PROCEED_WITH_CONDITIONS
    return current_state


def _derive_integrity_status(
    *,
    decision_valid: bool,
    confidence_gate_passed: bool,
    evidence_gaps: list[str],
    invalid_signal_dominance: bool,
    invalid_signals: list[str],
    conflict_flags: list[str],
    risk_stack: list[DecisionRiskItem],
    execution_floor_result: ExecutionFloorResult,
) -> IntegrityState:
    if (
        not decision_valid
        or not confidence_gate_passed
        or invalid_signal_dominance
        or evidence_gaps
    ):
        return IntegrityState.INVALID
    if len(risk_stack) >= 2 or not execution_floor_result.passed:
        return IntegrityState.AT_RISK
    if conflict_flags or invalid_signals:
        return IntegrityState.MIXED
    return IntegrityState.CLEAN


def _build_conditions(
    *,
    decision_state: DecisionState,
    evidence_gaps: list[str],
    risk_stack: list[DecisionRiskItem],
) -> list[str]:
    conditions: list[str] = []

    for dimension in evidence_gaps:
        conditions.append(
            f"Collect additional behavioural evidence for {dimension} before relying on the decision."
        )

    for risk in risk_stack:
        if risk.risk_code == "execution_negative_medium_confidence":
            conditions.append("Probe execution reliability through targeted references and delivery checkpoints.")
        elif risk.risk_code == "critical_dimension_failure":
            conditions.append(
                f"Run a focused behavioural follow-up on {risk.source_dimension} before final commitment."
            )
        elif risk.risk_code == "minimum_dimension_risk":
            conditions.append(
                f"Set probation monitoring for {risk.source_dimension} with explicit behavioural checkpoints."
            )
        elif risk.risk_code == "priority_dimension_negative":
            conditions.append(
                f"Investigate the behavioural concern in {risk.source_dimension} before proceeding."
            )

    ordered: list[str] = []
    seen: set[str] = set()
    for condition in conditions:
        if condition not in seen:
            ordered.append(condition)
            seen.add(condition)

    if decision_state is DecisionState.PROCEED_WITH_CONDITIONS and risk_stack and not ordered:
        ordered.append("Proceed only with explicit behavioural follow-up conditions.")
    return ordered


def _build_trade_off_statement(decision_state: DecisionState) -> str:
    if decision_state is DecisionState.PROCEED:
        return "Proceeding on behavioural evidence with no active non-overridable blockers."
    if decision_state is DecisionState.PROCEED_WITH_CONDITIONS:
        return "Behavioural evidence supports progress, but only with explicit conditions and follow-up."
    if decision_state is DecisionState.DO_NOT_PROCEED:
        return "Sufficient negative behavioural evidence triggered non-overridable decision rules."
    return "Required behavioural evidence is not strong enough to support a valid decision."


def _build_rationale(
    *,
    decision_state: DecisionState,
    critical_result: dict[str, Any],
    evidence_result: dict[str, Any],
    risk_stack: list[DecisionRiskItem],
    execution_floor_result: ExecutionFloorResult,
) -> str:
    if decision_state is DecisionState.INSUFFICIENT_EVIDENCE:
        reasons = evidence_result["evidence_gaps"] or evidence_result["invalid_required_dimensions"]
        reason_text = ", ".join(reasons) if reasons else "required behavioural dimensions"
        return (
            "Behaviour-only decisioning returned INSUFFICIENT_EVIDENCE because the required "
            f"behavioural evidence was not reliable enough to evaluate: {reason_text}."
        )
    if decision_state is DecisionState.DO_NOT_PROCEED:
        blockers = critical_result["hard_failures"] or critical_result["soft_failures"]
        blocker_text = ", ".join(blockers) if blockers else "stacked behavioural risks"
        if execution_floor_result.trigger_rule == "execution_floor_reject":
            blocker_text = "execution floor breach"
        return (
            "Behaviour-only decisioning returned DO_NOT_PROCEED because sufficient negative "
            f"behavioural evidence triggered non-overridable rules: {blocker_text}."
        )
    if decision_state is DecisionState.PROCEED_WITH_CONDITIONS:
        risk_dimensions = [risk.source_dimension for risk in risk_stack]
        risk_text = ", ".join(_canonicalise_dimensions(risk_dimensions)) or "borderline behavioural evidence"
        return (
            "Behaviour-only decisioning returned PROCEED_WITH_CONDITIONS because the evidence "
            f"is usable but requires monitoring or follow-up on: {risk_text}."
        )
    return (
        "Behaviour-only decisioning returned PROCEED because critical behavioural thresholds "
        "were met without blocking risks."
    )


def _build_audit_trace(
    *,
    decision_input: BehaviouralDecisionInput,
    evidence_result: dict[str, Any],
    confidence_gate_passed: bool,
    confidence: ConfidenceBand,
    execution_floor_result: ExecutionFloorResult,
    critical_result: dict[str, Any],
    minimum_result: dict[str, Any],
    priority_result: dict[str, Any],
    risk_stack: list[DecisionRiskItem],
    decision_state: DecisionState,
    integrity_status: IntegrityState,
    final_resolution_path: list[str],
    invalid_signal_dominance: bool,
) -> list[DecisionAuditEntry]:
    return [
        DecisionAuditEntry(
            code=RULE_ENFORCEMENT_ACTIVE_MARKER,
            message="MVP1 behavioural rule slice is actively enforced in the dark Decision Layer.",
            details={
                "rule_version": decision_input.rule_version,
                "policy_version": decision_input.policy_version,
                "skills_inputs_excluded": True,
            },
        ),
        DecisionAuditEntry(
            code="evidence_sufficiency_result",
            message="Evidence sufficiency evaluated for required behavioural dimensions.",
            details=evidence_result,
        ),
        DecisionAuditEntry(
            code="confidence_gate_result",
            message="Confidence gate evaluated using critical behavioural dimensions only.",
            details={
                "passed": confidence_gate_passed,
                "confidence": confidence.value,
                "invalid_signal_dominance": invalid_signal_dominance,
            },
        ),
        DecisionAuditEntry(
            code="execution_floor_result",
            message="Execution floor evaluated as a global behavioural constraint.",
            details=execution_floor_result.model_dump(mode="python"),
        ),
        DecisionAuditEntry(
            code="critical_dimension_result",
            message="Critical behavioural dimensions were checked against signed thresholds.",
            details=critical_result,
        ),
        DecisionAuditEntry(
            code="minimum_dimension_result",
            message="Minimum behavioural dimensions were checked for risk contribution.",
            details=minimum_result,
        ),
        DecisionAuditEntry(
            code="priority_dimension_result",
            message="Priority behavioural dimensions were applied after blockers and risk stack.",
            details={
                "status": priority_result["status"],
                "positive_dimensions": priority_result["positive_dimensions"],
                "negative_dimensions": priority_result["negative_dimensions"],
            },
        ),
        DecisionAuditEntry(
            code="risk_stack_result",
            message="Structured behavioural risk stack calculated deterministically.",
            details={
                "risk_count": len(risk_stack),
                "risks": [risk.model_dump(mode="python") for risk in risk_stack],
            },
        ),
        DecisionAuditEntry(
            code="final_resolution_path",
            message="Final decision resolved through deterministic behavioural rule precedence.",
            details={
                "path": final_resolution_path,
                "decision_state": decision_state.value,
                "integrity_status": integrity_status.value,
            },
        ),
    ]


def _required_level(
    *,
    dimension: str,
    critical_dimensions: list[str],
    minimum_dimensions: list[str],
    priority_dimensions: list[str],
) -> str:
    if dimension in critical_dimensions:
        return "critical"
    if dimension in minimum_dimensions:
        return "minimum"
    if dimension in priority_dimensions:
        return "priority"
    return "observed"


def _classify_dimension_threshold(
    *,
    score_internal: int,
    confidence: ConfidenceBand,
    has_valid_signals: bool,
    required_level: str,
) -> tuple[str, str]:
    if not has_valid_signals:
        return "insufficient_evidence", "insufficient_evidence"

    if required_level == "critical":
        if _confidence_order(confidence) < _confidence_order(ConfidenceBand.MEDIUM):
            return "insufficient_evidence", "insufficient_evidence"
        if score_internal >= 1:
            return "met", "pass"
        if score_internal == 0:
            return "borderline", "watch"
        return "not_met", "risk"

    if required_level == "minimum":
        if score_internal >= 0:
            return "met", "pass"
        if _confidence_order(confidence) >= _confidence_order(ConfidenceBand.MEDIUM):
            return "not_met", "risk"
        return "borderline", "watch"

    if required_level == "priority":
        if _confidence_order(confidence) < _confidence_order(ConfidenceBand.MEDIUM):
            return "borderline", "watch"
        if score_internal >= 1:
            return "met", "pass"
        if score_internal <= -1:
            return "not_met", "risk"
        return "borderline", "watch"

    if score_internal >= 1:
        return "observed_positive", "pass"
    if score_internal <= -1:
        return "observed_negative", "risk"
    return "observed_neutral", "watch"


def _has_invalid_signal_dominance(
    *,
    dimension_contexts: list[dict[str, Any]],
    required_dimensions: list[str],
) -> bool:
    required_contexts = [
        context for context in dimension_contexts if context["dimension"] in required_dimensions
    ]
    invalid_total = sum(len(context["invalid_signals"]) for context in required_contexts)
    valid_total = sum(len(context["valid_signals"]) for context in required_contexts)
    return invalid_total > valid_total and invalid_total > 0


def _add_risk(
    risk_stack: list[DecisionRiskItem],
    *,
    risk_code: str,
    severity: RiskSeverity,
    source_dimension: str,
    trigger_rule: str,
) -> None:
    candidate = (risk_code, source_dimension, trigger_rule)
    existing = {
        (risk.risk_code, risk.source_dimension, risk.trigger_rule)
        for risk in risk_stack
    }
    if candidate in existing:
        return
    risk_stack.append(
        DecisionRiskItem(
            risk_code=risk_code,
            severity=severity,
            source_dimension=source_dimension,
            trigger_rule=trigger_rule,
        )
    )


def _canonicalise_dimensions(dimensions: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for dimension in CANONICAL_BEHAVIOURAL_DIMENSIONS:
        if dimension in dimensions and dimension not in seen:
            ordered.append(dimension)
            seen.add(dimension)
    return ordered


def _flatten_signal_list(items: list[list[str]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in items:
        for value in group:
            if value not in seen:
                ordered.append(value)
                seen.add(value)
    return ordered


def _confidence_order(confidence: ConfidenceBand | None) -> int:
    return _CONFIDENCE_ORDER[confidence or ConfidenceBand.LOW]


__all__ = [
    "DECISION_LAYER_POLICY_VERSION",
    "DECISION_LAYER_RULE_VERSION",
    "RULE_ENFORCEMENT_ACTIVE_MARKER",
    "evaluate_behavioural_decision",
]
