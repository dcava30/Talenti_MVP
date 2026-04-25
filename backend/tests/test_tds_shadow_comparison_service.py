from __future__ import annotations

import pytest


def test_classify_shadow_comparison_mapping() -> None:
    from app.services.tds_shadow_comparison import classify_shadow_comparison

    assert (
        classify_shadow_comparison(
            legacy_score_present=True,
            legacy_recommendation="proceed",
            tds_decision_present=True,
            tds_decision_state="PROCEED",
        ).comparison_status
        == "aligned"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=True,
            legacy_recommendation="proceed",
            tds_decision_present=True,
            tds_decision_state="PROCEED_WITH_CONDITIONS",
        ).comparison_status
        == "shifted_more_cautious"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=True,
            legacy_recommendation="reject",
            tds_decision_present=True,
            tds_decision_state="PROCEED",
        ).comparison_status
        == "shifted_less_cautious"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=True,
            legacy_recommendation="proceed",
            tds_decision_present=True,
            tds_decision_state="INSUFFICIENT_EVIDENCE",
        ).comparison_status
        == "insufficient_evidence"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=True,
            legacy_recommendation="proceed",
            tds_decision_present=False,
            tds_decision_state=None,
        ).comparison_status
        == "legacy_only"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=False,
            legacy_recommendation=None,
            tds_decision_present=True,
            tds_decision_state="DO_NOT_PROCEED",
        ).comparison_status
        == "tds_only"
    )
    assert (
        classify_shadow_comparison(
            legacy_score_present=False,
            legacy_recommendation=None,
            tds_decision_present=False,
            tds_decision_state=None,
        ).comparison_status
        == "insufficient_data"
    )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("PASS", "observed"),
        ("REVIEW", "needs_review"),
        ("FAIL", "missing"),
        ("", "unavailable"),
        (None, "unavailable"),
        ("unexpected", "unavailable"),
    ],
)
def test_normalize_legacy_skills_outcome_status(raw_value: str | None, expected: str) -> None:
    from app.services.tds_shadow_comparison import normalize_legacy_skills_outcome_status

    assert normalize_legacy_skills_outcome_status(raw_value) == expected
