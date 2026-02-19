from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _clear_app_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]


def _load_backend_modules():
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/app.db")
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    _clear_app_modules()
    from app.schemas.scoring import ScoringRequest
    from app.services import ml_client as ml_client_module
    from app.services.culture_fit import load_org_culture_context
    from app.models import Organisation

    return ScoringRequest, ml_client_module, load_org_culture_context, Organisation


def _load_model_service_modules():
    service_root = str(ROOT / "model-service-1")
    if service_root not in sys.path:
        sys.path.insert(0, service_root)
    _clear_app_modules()
    from app.model import ModelPredictor
    import model_draft

    return ModelPredictor, model_draft


def _report(name: str, ok: bool, details: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    suffix = f" - {details}" if details else ""
    print(f"{status}: {name}{suffix}")


def main() -> int:
    ScoringRequest, ml_client_module, load_org_culture_context, Organisation = _load_backend_modules()
    ModelPredictor, model_draft = _load_model_service_modules()

    sample_env = {
        "control_vs_autonomy": "execution_led",
        "outcome_vs_process": "process_led",
        "conflict_style": "alignment_focused",
        "decision_reality": "evidence_led",
        "ambiguity_load": "well_defined",
        "high_performance_archetype": "reliable_executor",
        "dimension_weights": {"autonomy": 0.8, "decision_style": 0.2},
        "fatal_risks": [],
        "coachable_risks": [],
    }

    sample_taxonomy = {
        "taxonomy_id": "org_taxonomy_v2",
        "version": "2026.02",
        "signals": [
            {
                "signal_id": "bias_to_action",
                "dimension": "decision_style",
                "description": "Acts quickly with trade-offs.",
                "score_map": {"strong": 3, "moderate": 2, "weak": 0, "not_observed": 0},
                "evidence_hints": ["decide", "trade-off"],
            },
            {
                "signal_id": "accountability",
                "dimension": "autonomy",
                "description": "Owns outcomes and learns from mistakes.",
                "score_map": {"strong": 3, "moderate": 2, "weak": -1, "not_observed": 0},
                "evidence_hints": ["owned", "responsible"],
            },
        ],
    }

    # Check A: org inputs passed end-to-end (schema + payload + engine trace)
    schema_fields = getattr(ScoringRequest, "model_fields", {})
    schema_ok = "operating_environment" in schema_fields and "taxonomy" in schema_fields
    client = ml_client_module.MLClient()
    payload = client._build_model1_payload(
        [{"speaker": "candidate", "content": "I owned the decision."}],
        operating_environment=sample_env,
        taxonomy=sample_taxonomy,
        trace=True,
    )
    payload_ok = "operating_environment" in payload and "taxonomy" in payload

    predictor = ModelPredictor()
    predictor.load_model()
    result = predictor.predict(
        [
            {
                "speaker": "candidate",
                "content": "I decided quickly and owned the outcome.",
                "candidate_id": "cand-1",
                "role_id": "role-1",
                "department_id": "dept-1",
                "interview_id": "int-1",
            }
        ],
        operating_environment=sample_env,
        taxonomy=sample_taxonomy,
        trace=True,
    )
    trace = result.get("metadata", {}).get("trace", {})
    trace_ok = bool(trace) and trace.get("operating_environment") is not None
    _report(
        "Org inputs passed end-to-end (API -> model -> engine)",
        schema_ok and payload_ok and trace_ok,
        "trace enabled" if trace_ok else "trace missing",
    )

    # Check B: TeamOperatingEnvironment differs from example defaults
    default_env = model_draft.example_env()
    trace_env = trace.get("operating_environment", {})
    diff = (
        trace_env.get("control_vs_autonomy") != default_env.control_vs_autonomy
        or trace_env.get("outcome_vs_process") != default_env.outcome_vs_process
        or trace_env.get("conflict_style") != default_env.conflict_style
    )
    _report(
        "TeamOperatingEnvironment differs from example defaults",
        diff,
        f"control_vs_autonomy={trace_env.get('control_vs_autonomy')}",
    )

    # Check C: dimension_weights affect weighted_score + alignment
    taxonomy = model_draft.build_taxonomy_version(sample_taxonomy)
    classifications = [
        model_draft.SignalClassification(
            signal_id="bias_to_action",
            level="weak",
            confidence=0.9,
            evidence=[model_draft.EvidenceSpan(turn_index=0, quote="waited", rationale="test")],
        ),
        model_draft.SignalClassification(
            signal_id="accountability",
            level="strong",
            confidence=0.9,
            evidence=[model_draft.EvidenceSpan(turn_index=0, quote="owned it", rationale="test")],
        ),
    ]
    classifier = model_draft.StubClassifier()
    classifier.classify = lambda artifact, taxonomy: classifications  # type: ignore[assignment]
    engine = model_draft.DecisionDominantEngine(classifier=classifier, policy=model_draft.EnginePolicy())
    artifact = model_draft.InterviewArtifact(
        candidate_id="cand-1",
        role_id="role-1",
        department_id="dept-1",
        interview_id="int-1",
        interview_datetime_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        turns=[model_draft.TranscriptTurn(speaker="candidate", text="I owned it.")],
    )
    env_a = model_draft.build_team_operating_environment(
        {**sample_env, "dimension_weights": {"autonomy": 0.9, "decision_style": 0.1}}
    )
    env_b = model_draft.build_team_operating_environment(
        {**sample_env, "dimension_weights": {"autonomy": 0.1, "decision_style": 0.9}}
    )
    report_a = engine.generate_report(artifact, env_a, taxonomy)
    report_b = engine.generate_report(artifact, env_b, taxonomy)
    weights_ok = report_a.overall_alignment != report_b.overall_alignment
    _report(
        "Dimension weights affect weighted_score and alignment",
        weights_ok,
        f"{report_a.overall_alignment} vs {report_b.overall_alignment}",
    )

    # Check D: taxonomy loaded from org context (not example)
    org_values = {
        "operating_environment": sample_env,
        "taxonomy": sample_taxonomy,
    }
    org = Organisation(name="Test Org", values_framework=json.dumps(org_values))
    _, loaded_tax = load_org_culture_context(org)
    taxonomy_ok = loaded_tax.get("taxonomy_id") == "org_taxonomy_v2"
    _report(
        "Taxonomy loaded from org context (not example)",
        taxonomy_ok,
        f"taxonomy_id={loaded_tax.get('taxonomy_id')}",
    )

    # Check StubClassifier usage
    stub_in_use = trace.get("classifier") == "StubClassifier"
    _report(
        "StubClassifier not used in production path",
        not stub_in_use,
        f"classifier={trace.get('classifier')}",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
