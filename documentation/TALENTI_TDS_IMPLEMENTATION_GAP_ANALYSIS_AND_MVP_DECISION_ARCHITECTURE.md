# Talenti TDS Implementation Gap Analysis and MVP Decision Architecture

Notation:
- Confirmed evidence = current repository or source-document evidence with file and line references where available.
- Recommendation = target-state MVP architecture or product decision required to align the stack to TDS.
- Governing rule for this report: **Behaviour decides. Skills informs.**

## 1. Executive Summary

### Confirmed evidence

The current system is a mixed architecture:
- The Talenti MVP backend orchestrates both model services, persists `interview_scores` and `score_dimensions`, and computes a culture-fit recommendation, but it does not own a first-class final TDS decision contract. Evidence: `backend/app/services/interview_scoring.py:651-686`, `backend/app/models/interview_score.py:11-47`, `backend/app/models/score_dimension.py:10-38`.
- The product still presents itself as a dual-scorecard and recruiter decision-support platform, not a behavioural decision system. Evidence: `documentation/ARCHITECTURE_OVERVIEW.md:59-64`, `documentation/ARCHITECTURE_OVERVIEW.md:85-90`, `documentation/USER_GUIDE.md:219-224`, `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2062`.
- Ranking and score-first behaviour remain first-class in API and UI. Evidence: `backend/app/api/shortlist.py:11-18`, `backend/app/schemas/shortlist.py:4-16`, `src/lib/pages/RoleDetails.jsx:85-90`, `src/lib/components/ShortlistView.jsx:29-32`, `src/lib/components/CandidateComparison.jsx:131-213`.
- Model Service 1 currently emits decision-like fields such as `recommendation`, `overall_alignment`, and `overall_risk_level`. Evidence: `model-service-1/app/schemas.py:94-117`, `model-service-1/app/model.py:259-311`.
- Model Service 2 currently emits outcome-like fields such as `overall_score`, `outcome`, `must_haves_passed`, `must_haves_failed`, `gaps`, and `summary`. Evidence: `model-service-2/app/schemas.py:45-55`, `model-service-2/app/model.py:213-274`, `model-service-2/model_draft.py:230-253`.

The TDS draft requires the system to become a behavioural decisioning platform:
- MVP1 TDS explicitly says it does not assess technical or functional skills, does not rank candidates, and decides only whether a candidate should Proceed, Proceed with Conditions, Do Not Proceed, or be returned as Insufficient Evidence / No Judgement. Evidence: TDS draft PDF pages 5-6.
- The draft also requires deterministic rule enforcement rather than free-form LLM judgement. Evidence: TDS draft PDF page 61.

### Recommendation

The most important architectural change is to introduce a backend **Decision Layer** inside the Talenti MVP backend that:
- consumes behavioural evidence only,
- applies deterministic TDS rules,
- owns `decision_state`, `decision_valid`, `confidence_gate_passed`, `integrity_status`, `risk_stack`, conditions, rationale, and audit trace,
- becomes the only authoritative source of the MVP1 final decision.

Why MVP1 final decisioning must be behavioural only:
- The TDS draft excludes technical and functional skills from MVP1 decisioning. Evidence: TDS draft PDF page 5.
- The final decision must be derived from observed behavioural evidence evaluated against role and environment requirements, not from a blended “best overall candidate” concept. Evidence: TDS draft PDF pages 5-10, 34-37.

How Model Service 2 should be retained:
- Model Service 2 should remain in the system as the producer of a separate organisational artifact named **Skills Assessment Summary**.
- That artifact can surface observed competencies, competency coverage, skill gaps, evidence strength, confidence, and source references.

Why the Skills Assessment Summary must not influence final TDS decisioning:
- Allowing skills outputs to change `decision_state`, `decision_valid`, `confidence_gate_passed`, `integrity_status`, `risk_stack`, or behavioural rationale would directly contradict the MVP1 TDS scope boundary.
- It would also recreate the current ambiguity where recruiters see two “decision-like” outputs and infer an overall hiring recommendation from them.

## 2. TDS Canonical MVP1 Requirements

### Confirmed evidence from the TDS draft

| Requirement area | Canonical MVP1 requirement | Source |
|---|---|---|
| Behavioural dimensions | The behavioural dimensions are `ownership`, `execution`, `challenge`, `ambiguity`, and `feedback`. Model Service 1 already uses this canonical set. | TDS draft PDF pages 18-19; `model-service-1/talenti_dimensions.py:42-48` |
| Signal validity rules | Only observed behavioural evidence counts. Generic, rehearsed, hypothetical, unverifiable, or invalid signals must be excluded. | TDS draft PDF pages 9-10, 62, 66 |
| Internal score scale | Per-dimension internal score scale is `-2` to `+2`, where `0` means not observed or insufficient evidence. Scores are internal evidence, not the product output. | TDS draft PDF pages 6, 18, 60 |
| Confidence rules | Confidence is separate from score and is an evidence-reliability gate, not a display-first field. Valid bands are Low, Medium, High. | TDS draft PDF pages 6, 19-22, 30, 37 |
| Evidence thresholds | A dimension needs at least one valid signal with clear action, outcome, and ownership before scoring. Otherwise score defaults to `0` and confidence to Low. | TDS draft PDF pages 9, 20-22 |
| Conflict rules | Contradictory evidence within a dimension caps score at `0` and marks integrity as conflicted/mixed. | TDS draft PDF pages 9, 17, 21, 28 |
| Execution floor | Execution is a global floor constraint. If execution is materially negative with sufficient confidence, the candidate cannot Proceed regardless of other strengths. | TDS draft PDF pages 24, 27, 40, 43, 45 |
| Risk stack | Risk is counted when a dimension is `<= -1` with confidence `>= Medium`. `2` risks require Proceed with Conditions. `3+` risks require Do Not Proceed. | TDS draft PDF page 29 |
| Environment mapping | The declared role/environment determines critical, minimum, and priority dimensions. Candidates are evaluated against that environment, not against each other. | TDS draft PDF pages 5, 9-10, 40-46 |
| Critical / minimum / non-critical classification | Critical dimensions must meet `>= +1`; minimum dimensions must meet `>= 0`; non-critical dimensions support depth and confidence but do not block decisions on their own. | TDS draft PDF pages 41-46 |
| Priority dimension rules | Priority dimensions only adjust borderline or Proceed-with-Conditions states after critical thresholds and risk stack have already been applied. They must not override critical failures, execution floor, or risk stack. | TDS draft PDF pages 35-36, 49-50 |
| Decision states | Final states are `Proceed`, `Proceed with Conditions`, `Do Not Proceed`, and `Insufficient Evidence (No Judgement)`. | TDS draft PDF pages 6, 34-35 |
| Integrity states | The draft is inconsistent: it references `clean / conflicted / insufficient` and later `Clean / Mixed / Invalid`. | TDS draft PDF pages 2, 6, 30-31 |
| Output contract | Every decision must include stance, strengths, risks, environment fit, trade-off statement, conditions where applicable, and traceability. | TDS draft PDF pages 53, 61 |
| Candidate feedback constraints | Candidate feedback must derive from system outputs but strip scores, confidence, and environment specificity in standard feedback. | TDS draft PDF pages 68-69 |

### Canonical MVP1 requirement freeze for implementation planning

Recommendation:
- MVP1 final decisioning is **behavioural only**.
- The internal behavioural score scale remains `-2` to `+2`.
- `Confidence` is a decision validity gate, not a recruiter-facing ranking or comparison field.
- `Execution` is a global floor constraint in every environment.
- `Critical` failures cannot be compensated for.
- `Priority` logic only affects borderline states and never rescues a critical failure or execution-floor breach.
- `Insufficient Evidence` must remain distinct from `Do Not Proceed`.
- LLMs may extract or structure evidence, but deterministic backend rules must produce the final decision.

Recommended integrity state freeze for MVP1:
- `Clean`
- `Mixed`
- `At Risk`
- `Invalid`

Rationale:
- This aligns the implementation plan with the product clarification supplied for this analysis while still honouring the draft’s underlying reliability/stability intent.

## 3. TDS Skills Boundary

### Recommendation

Model Service 2 should be treated as the producer of a separate artifact called **Skills Assessment Summary**.

Definition:
- A separate organisational evidence artifact
- Not part of the TDS final decision
- Not part of cultural fit scoring
- Not part of behavioural decision logic
- Not part of ranking
- Not a pass/fail hiring recommendation

Allowed Skills Assessment Summary outputs:
- Observed competencies
- Competency coverage
- Skill gaps
- Evidence strength
- Confidence
- Source references
- Human-readable skills summary
- `Requires human review` where appropriate

Disallowed Skills Assessment Summary outputs:
- PASS / FAIL as hiring outcome
- Final recommendation
- Candidate ranking
- Overall hiring score
- Decision state
- “Best candidate” language
- Anything that modifies the TDS behavioural decision

Recommended product language:
- `Skills Assessment Summary`
- `Observed Skills Evidence`
- `Competency Coverage`
- `Skills Gaps`
- `Evidence Strength`
- `Requires Human Review`

Avoid product language:
- `Skills Fit Score`
- `Technical Fit Rank`
- `AI Skills Ranking`
- `Pass / Fail`
- `Recommended based on skills`
- `Best skilled candidate`

### Confirmed evidence of the current boundary problem

| Current implementation | Evidence | Why it must change |
|---|---|---|
| Model Service 2 returns `overall_score` and `outcome` (`PASS/REVIEW/FAIL`) | `model-service-2/app/schemas.py:45-55`, `model-service-2/app/model.py:213-274` | This makes the skills service look like a hiring decision engine |
| Talenti persists `skills_score` and `skills_outcome` beside behavioural recommendation | `backend/app/models/interview_score.py:20-27`, `backend/app/services/interview_scoring.py:533-546` | This makes skills appear co-equal with behavioural decisioning |
| Recruiter UI shows skills outcome badges and score percentages | `src/lib/pages/RoleDetails.jsx:261-281`, `src/lib/pages/InterviewReport.jsx:412-449`, `src/lib/components/SkillsFitCard.jsx:56-168` | This presents a decision-like artefact rather than an informational summary |
| Comparison UI uses skills score and outcome as side-by-side candidate discriminators | `src/lib/components/CandidateComparison.jsx:170-213` | This encourages ranking and comparative decisioning from skills |

## 4. TDS Internal Contradictions / Product Questions

| Issue | Conflict or ambiguity | Why it matters | Recommended resolution |
|---|---|---|---|
| Skills excluded from MVP1 decisioning, but later skills confidence is referenced | Page 5 excludes technical and functional skills in MVP1, while page 2 references “Behavioural Confidence + Skills Confidence” and page 66 defines skills signal validation rules. | Without a boundary, teams may incorrectly wire skills into final decision validity or outcome logic. | **Freeze the rule that skills assessment is retained as a separate Skills Assessment Summary artifact, but is excluded from MVP1 final TDS decisioning.** |
| Do Not Proceed vs Insufficient Evidence | Page 6 says Do Not Proceed can result from “consistent negative or insufficient evidence,” while pages 35, 41, and 45 define Insufficient Evidence as its own no-judgement state. | This is a core policy distinction. If unresolved, the system will incorrectly treat missing evidence as negative evidence. | `Do Not Proceed` should require sufficient negative behavioural evidence. `Insufficient Evidence / No Judgement` should be used when evidence is missing, invalid, too thin, or confidence-gated. |
| LLM decisioning vs deterministic backend decisioning | The draft includes prompt-level rule examples, but page 61 also says “Decision engine rules must be coded, not interpreted” and “LLM does not decide freely.” | If model-service outputs remain authoritative, the system will not meet the draft’s determinism requirement. | Keep LLMs for extraction, structure, and evidence summarisation only. The Talenti MVP backend Decision Layer must resolve the final behavioural decision. |
| Whether score language is internal only | The draft defines a `-2` to `+2` scale internally, but the decision contract and candidate feedback sections strip or de-emphasise score presentation. | Score-first UX will reintroduce ranking and recruiter interpretation rather than final decision resolution. | Treat scores as internal evidence. Do not make score percentages or score overrides the primary product surface. |
| Recruiter override vs non-overridable constraints | Pages 24, 36, 43, and 49 say critical failures, execution floor, and some constraints cannot be overridden, while page 53 introduces override capture. | The current product already exposes “override score” behaviour, so the governance boundary must be explicit. | Replace “override score” with auditable human review / exception handling. Human action may record disagreement, but it must not silently bypass policy guardrails. |
| Candidate feedback as MVP or future state | Pages 68-69 define a candidate feedback layer, but the implementation scope is not pinned and the current product still exposes raw score language to candidates. | Candidate feedback is governance-sensitive and easy to mis-scope into the core decisioning rewrite. | Treat candidate feedback as a later controlled output layer after the behavioural Decision Layer and decision schema are stable. |
| Integrity taxonomy inconsistency | The draft alternates between `clean / conflicted / insufficient` and `Clean / Mixed / Invalid`. | Without a frozen state model, DB/API/UX contracts will drift again. | Freeze MVP1 integrity states to `Clean / Mixed / At Risk / Invalid`, and map draft terms such as conflicted/insufficient into those states. |

## 5. Current Codebase vs TDS Matrix

| TDS requirement | Current implementation | Repo/file evidence | Status | Required change |
|---|---|---|---|---|
| MVP1 final decisioning is behavioural only | Backend computes only a culture recommendation, but product stores and surfaces skills outputs as co-equal interview outputs | `backend/app/services/interview_scoring.py:651-686`, `backend/app/models/interview_score.py:20-27`, `src/lib/pages/InterviewReport.jsx:412-449` | Partial / contradicted | Introduce behavioural-only Decision Layer and demote skills to separate artifact |
| Skills Assessment Summary is separate from MVP1 decisioning | No such boundary exists; Model Service 2 emits `overall_score` and `outcome`, Talenti stores `skills_score` / `skills_outcome`, and UI renders PASS/FAIL-style skills outcomes | `model-service-2/app/schemas.py:45-55`, `backend/app/models/interview_score.py:20-27`, `src/lib/components/SkillsFitCard.jsx:56-168` | Missing / contradicted | Rename and reframe Model Service 2 outputs as Skills Assessment Summary; exclude from decision inputs |
| Final decision state must be first-class | No `decision_state` exists in DB, API, or frontend | Search evidence in `documentation/TALENTI_DECISIONING_ALIGNMENT_INVESTIGATION.md:35`, plus current models in `backend/app/models/interview_score.py:11-47` | Missing | Add decision-first schema, API, and UX |
| Insufficient Evidence / No Judgement must be distinct | Current backend recommendation outcomes are `proceed/caution/reject`; no insufficient-evidence state is represented | `backend/app/services/interview_scoring.py:296-418`, `backend/app/models/interview_score.py:24-31` | Missing | Add explicit insufficient-evidence handling in Decision Layer |
| Deterministic backend must own final decision | Model Service 1 and Model Service 2 both emit decision-like outputs | `model-service-1/app/schemas.py:94-117`, `model-service-2/app/schemas.py:45-55` | Contradicted | Make model-service outputs intermediate evidence only |
| Confidence is a validity gate, not a recruiter-first display | Confidence exists in model and backend logic, but not as a first-class decision-validity contract | `backend/app/services/interview_scoring.py:247-256`, `model-service-1/talenti_dimensions.py:635-714` | Partial | Add `decision_valid` and `confidence_gate_passed` to final decision schema |
| Integrity must be a structured reliability classification | Current stack has anti-cheat risk and some contradiction handling, but no first-class integrity state | `src/lib/pages/InterviewReport.jsx:451-473`, `backend/app/services/interview_scoring.py:247-256` | Partial | Add `integrity_status`, invalid signals, and conflict flags to decision output |
| Execution is a global floor constraint | Backend risk stack partially reflects behavioural risk logic, but there is no explicit execution-floor contract in API/DB/UX | `backend/app/services/interview_scoring.py:296-418` | Partial | Make execution-floor result explicit in the Decision Layer and schema |
| Critical / minimum / priority dimensions must be explicit | Current role rubric stores weights and tiers, but these live under score/rubric semantics and are recruiter-editable | `backend/app/schemas/roles.py:56-109`, `backend/app/api/roles.py:142-173`, `backend/app/models/job_role.py:24-26` | Partial / contradicted | Recast role inputs as policy mapping inputs, not editable scorecards |
| TDS does not rank candidates | Ranking is implemented in shortlist API and frontend sorting/comparison | `backend/app/api/shortlist.py:11-18`, `src/lib/pages/RoleDetails.jsx:85-90`, `src/lib/components/ShortlistView.jsx:29-32`, `src/lib/components/CandidateComparison.jsx:131-213` | Contradicted | Quarantine shortlist/ranking flows and replace with decision buckets |
| Scores are internal evidence, not the product output | Frontend prominently shows `% Match`, `Overall Score`, `Skills Fit`, and score overrides; candidate portal also shows score percentages | `src/lib/pages/RoleDetails.jsx:240-281`, `src/lib/pages/InterviewReport.jsx:346-392`, `src/lib/pages/CandidatePortal.jsx:195-200`, `src/lib/pages/CandidatePortal.jsx:282-300` | Contradicted | Replace score-first surfaces with decision outcome, rationale, risks, and conditions |
| Audit trace and policy versioning must be first-class | Raw payloads and environment input lineage are stored, but no unified decision audit trail exists | `backend/app/models/interview_score.py:35-46`, `backend/app/api/orgs.py:244-319`, `backend/app/api/interview_scores.py:52-100` | Partial | Add decision audit tables and policy/rule versioning |
| Candidate feedback must be constrained | Current product exposes candidate-facing score and feedback concepts without TDS stripping rules | `src/lib/pages/CandidatePortal.jsx:251-315`, TDS draft PDF pages 68-69 | Partial / contradicted | Add a controlled candidate-feedback layer after decision policy is stable |

Specific finding for Model Service 2:
- No evidence was found that `skills_score` or `skills_outcome` currently change the backend’s behavioural `recommendation`. The direct decision logic in `compute_risk_stack()` is behavioural-only. Evidence: `backend/app/services/interview_scoring.py:296-418`.
- However, Model Service 2 strongly influences **product interpretation** because its outputs are stored alongside behavioural recommendation and displayed as PASS/FAIL-style hiring signals in recruiter and comparison UI. Evidence: `backend/app/models/interview_score.py:20-27`, `src/lib/pages/InterviewReport.jsx:412-449`, `src/lib/components/CandidateComparison.jsx:170-213`.

## 6. MVP Decision Layer Specification

### Recommendation

Add a dedicated backend **Decision Layer** in the Talenti MVP backend.

Proposed location:
- `backend/app/services/decision_layer.py` for a minimal insertion path, or
- `backend/app/services/decisioning/` if the team wants a dedicated module boundary.

Minimal placement in current flow:
- Keep model orchestration in `backend/app/services/interview_scoring.py`.
- After behavioural evidence extraction and environment loading, call the Decision Layer before persistence.
- Persist Decision Layer outputs into a new decision-first schema rather than relying on `interview_scores` as the final contract.

The Decision Layer must own:
- `final decision_state`
- `decision_valid`
- `confidence_gate_passed`
- `integrity_status`
- `evidence sufficiency`
- `critical dimension enforcement`
- `minimum dimension enforcement`
- `priority dimension adjustment`
- `execution floor`
- `conflict resolution`
- `risk accumulation`
- `trade_off_statement`
- `conditions`
- `insufficient evidence handling`
- `audit trace`

The Decision Layer must consume:
- behavioural dimension evidence,
- environment profile,
- environment-derived dimension classification,
- conflict flags,
- invalid signal flags,
- rule/policy versions,
- human review actions where applicable.

The Decision Layer must not consume:
- `skills_score`
- `skills_outcome`
- `must_haves_passed`
- `must_haves_failed`
- `gaps`
- `summary` from Model Service 2
- any Skills Assessment Summary output as a decision input

### Confirmed implementation seed to preserve

The current backend already contains useful precursors:
- `classify_dimensions()` is the right seed for per-dimension threshold application. Evidence: `backend/app/services/interview_scoring.py:204-291`.
- `compute_risk_stack()` is the right seed for deterministic behavioural decision logic, but its outputs are too limited for full TDS. Evidence: `backend/app/services/interview_scoring.py:296-418`.
- `org_environment` lineage and confidence are already preserved and should remain inputs to decision validity. Evidence: `backend/app/api/orgs.py:244-319`, `backend/app/api/orgs.py:404-425`.

Explicit MVP1 boundary:
- **The Decision Layer must consume behavioural evidence only for MVP1 final decisioning.**
- **It must not consume Skills Assessment Summary outputs as decision inputs.**

## 7. Model Service Boundary Redesign

### Model Service 1 — Cultural Fit / Behavioural Fit

#### Confirmed evidence

Model Service 1 currently returns:
- behavioural scores,
- confidence,
- rationale,
- `overall_alignment`,
- `overall_risk_level`,
- `recommendation`,
- `dimension_outcomes`,
- `env_requirements`.

Evidence:
- `model-service-1/app/schemas.py:94-117`
- `model-service-1/app/model.py:259-311`
- `model-service-1/talenti_dimensions.py:721-929`

#### Recommendation

Fields that can remain:
- `scores`
- `confidence`
- `rationale`
- `dimension_outcomes`
- `env_requirements`
- trace metadata

Fields that should be renamed or downgraded:
- `overall_alignment` -> `behavioural_alignment_signal`
- `overall_risk_level` -> `behavioural_risk_signal`
- `summary` -> `behavioural_evidence_summary`

Fields that should be treated as intermediate evidence only:
- `summary`
- `dimension_outcomes`
- `env_requirements`
- any model-side confidence rollup

Final decision-like fields that should no longer be authoritative:
- `recommendation`
- any implied final proceed/reject state in model output examples

Correct boundary:
- Model Service 1 extracts and structures behavioural evidence.
- The Talenti MVP Decision Layer resolves the final TDS decision.

### Model Service 2 — Skills Fit

#### Confirmed evidence

Model Service 2 currently produces the following outcome-like fields:
- `overall_score`
- `outcome`
- `must_haves_passed`
- `must_haves_failed`
- `gaps`
- `summary`

Evidence:
- `model-service-2/app/schemas.py:45-55`
- `model-service-2/app/model.py:213-274`
- `model-service-2/model_draft.py:230-253`

Talenti MVP currently persists and surfaces those outputs in decision-adjacent places:
- `backend/app/models/interview_score.py:20-27`
- `backend/app/services/interview_scoring.py:533-546`
- `src/lib/pages/RoleDetails.jsx:261-281`
- `src/lib/pages/InterviewReport.jsx:412-449`
- `src/lib/components/SkillsFitCard.jsx:56-168`
- `src/lib/components/CandidateComparison.jsx:170-213`

#### Recommendation

Treat Model Service 2 as the producer of the **Skills Assessment Summary**.

Fields that should be retained as skills evidence:
- per-competency evidence currently in `scores`
- `gaps`
- evidence-derived confidence
- matched keywords
- years detected
- human-readable summary text, after wording cleanup

Fields that should be renamed or downgraded:
- `scores` -> `observed_competencies`
- `must_haves_passed` -> `required_competencies_observed`
- `must_haves_failed` -> `required_competencies_missing`
- `summary` -> `human_readable_skills_summary`

Fields that must not be treated as TDS decisions:
- `overall_score`
- `outcome`
- `PASS`
- `REVIEW`
- `FAIL`

Code paths where skills output currently influences product outputs:
- Storage alongside behavioural recommendation: `backend/app/models/interview_score.py:20-27`
- Returned in scoring results: `backend/app/schemas/scoring.py:116-127`, `backend/app/api/scoring.py:174-179`
- Recruiter-facing skills panels: `src/lib/pages/RoleDetails.jsx:261-281`, `src/lib/pages/InterviewReport.jsx:412-449`
- Decision-like skills card: `src/lib/components/SkillsFitCard.jsx:56-168`
- Comparative candidate view: `src/lib/components/CandidateComparison.jsx:170-213`

How to prevent skills output from affecting decision state, ranking, or behavioural rationale:
- remove `skills_score` and `skills_outcome` from the final decision entity,
- do not pass Model Service 2 outputs into the Decision Layer,
- remove PASS/FAIL-style language from recruiter and candidate UX,
- present skills only as a separate, labelled Skills Assessment Summary,
- do not allow skills outputs to appear in shortlist, comparison, or decision badges.

## 8. Target Decision Output Schema

### MVP behavioural decision schema

Recommendation:

```json
{
  "decision_id": "uuid",
  "interview_id": "uuid",
  "candidate_id": "uuid",
  "role_id": "uuid",
  "organisation_id": "uuid",
  "decision_state": "Proceed | Proceed with Conditions | Do Not Proceed | Insufficient Evidence",
  "decision_valid": true,
  "confidence": "low | medium | high",
  "confidence_gate_passed": true,
  "integrity_status": "Clean | Mixed | At Risk | Invalid",
  "environment_profile": {
    "control_vs_autonomy": "full_ownership",
    "outcome_vs_process": "results_first",
    "conflict_style": "challenge_expected",
    "decision_reality": "evidence_led",
    "ambiguity_load": "ambiguous",
    "high_performance_archetype": "strong_owner"
  },
  "critical_dimensions": ["execution", "ownership"],
  "minimum_dimensions": ["feedback"],
  "priority_dimensions": ["challenge"],
  "dimension_evaluations": [
    {
      "dimension": "execution",
      "score_internal": 1,
      "confidence": "medium",
      "required_level": "critical",
      "threshold_status": "met",
      "outcome": "pass",
      "evidence_summary": ["delivered under pressure", "clear measurable outcome"],
      "rationale": "Met critical execution threshold with medium confidence"
    }
  ],
  "evidence_gaps": ["feedback lacked repeated examples"],
  "invalid_signals": ["generic hypothetical answer rejected for ambiguity"],
  "conflict_flags": ["ownership evidence conflicted across two examples"],
  "risk_stack": [
    {
      "risk_code": "challenge_negative_medium_confidence",
      "severity": "medium",
      "source_dimension": "challenge"
    }
  ],
  "execution_floor_result": {
    "passed": true,
    "reason": "Execution did not violate the global floor"
  },
  "trade_off_statement": "Proceeding due to strong ownership and execution despite mixed challenge evidence.",
  "conditions": [
    "Probe challenge handling in reference checks",
    "Use structured delivery checkpoints in probation"
  ],
  "rationale": "Behavioural decision derived from deterministic backend rules applied to observed behavioural evidence only.",
  "audit_trace": {
    "signals_to_dimensions": [],
    "dimensions_to_rules": [],
    "rules_to_outcome": [],
    "service_versions": {
      "model_service_1": "2.0.0"
    }
  },
  "rule_version": "tds-behavioural-rules-v1",
  "policy_version": "org-decision-policy-v1",
  "created_at": "2026-04-24T00:00:00Z"
}
```

### Skills Assessment Summary schema

Recommendation:

```json
{
  "skills_summary_id": "uuid",
  "interview_id": "uuid",
  "candidate_id": "uuid",
  "role_id": "uuid",
  "organisation_id": "uuid",
  "observed_competencies": [
    {
      "competency": "python",
      "evidence_strength": "high",
      "confidence": "medium",
      "source_references": ["resume", "transcript_segment_12"]
    }
  ],
  "competency_coverage": {
    "required_competencies_observed": ["python", "azure"],
    "required_competencies_missing": ["rag"]
  },
  "skill_gaps": ["RAG delivery evidence was weak and incomplete"],
  "evidence_strength": "medium",
  "confidence": "medium",
  "source_references": ["resume", "transcript_segment_12", "transcript_segment_19"],
  "human_readable_summary": "Observed evidence suggests partial competency coverage with one important gap.",
  "requires_human_review": true,
  "excluded_from_tds_decisioning": true,
  "model_version": "3.0.0",
  "created_at": "2026-04-24T00:00:00Z"
}
```

## 9. Database Gap Analysis

### Confirmed evidence

| Current table / field | Current role | Evidence | Gap vs TDS |
|---|---|---|---|
| `interview_scores` | Mixed score summary and recommendation store | `backend/app/models/interview_score.py:11-47` | Still score-first and not a decision-first entity |
| `score_dimensions` | Per-dimension score rows | `backend/app/models/score_dimension.py:10-38` | Good intermediate evidence store, but naming and contract remain score-first |
| `job_roles.scoring_rubric` | Recruiter-owned score weighting and tier configuration | `backend/app/models/job_role.py:24-26`, `backend/app/schemas/roles.py:61-109` | Encourages score design instead of policy-governed decisioning |
| `audit_log` | Generic audit capture | Referenced in docs and app structure; no decision-specific schema surfaced here | Not specific enough for decision traceability |
| `post_hire_outcomes` | Outcome tracking tied to `interview_scores` | `backend/app/models/post_hire_outcome.py:17-65` | Links to legacy score entity rather than a final decision entity |
| `org_environment_inputs` | Strong lineage for environment derivation | `backend/app/api/orgs.py:244-319`, `backend/app/api/orgs.py:426-476` | Good foundation and should remain linked to decisions |

### Recommendation

Recommended new or renamed tables:
- `decision_outcomes`
- `decision_dimension_evaluations`
- `decision_signal_evidence`
- `decision_risk_flags`
- `decision_audit_trail`
- `decision_policy_versions`
- `human_review_actions`
- `skills_assessment_summaries`

Recommended mapping:

| Target table | Purpose | Notes |
|---|---|---|
| `decision_outcomes` | Authoritative behavioural decision record | Owns `decision_state`, validity, integrity, confidence gate, rationale, and versions |
| `decision_dimension_evaluations` | Per-dimension threshold and outcome evaluations | Can absorb the useful parts of `score_dimensions` |
| `decision_signal_evidence` | Traceable signal-level evidence and invalid-signal records | Needed for audit replay and defensibility |
| `decision_risk_flags` | Structured risk accumulation records | Supports risk stack and conditions generation |
| `decision_audit_trail` | Rule hits, transitions, and lineage | Separate from generic audit log |
| `decision_policy_versions` | Frozen versions of mapping and rule policy | Needed for reproducibility |
| `human_review_actions` | Audited exception handling and override capture | Replaces “override score” semantics |
| `skills_assessment_summaries` | Separate Skills Assessment Summary artifact | Must not be a dependency of `decision_outcomes` |

Skills table requirements:
- It must be linked to candidate, role, and interview.
- It must not be linked as an input to `decision_outcomes`.
- It must be queryable as a separate organisational artifact.
- It must not drive outcome buckets or ranking.

## 10. API Gap Analysis

### APIs to add

Recommendation:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/decisions/evaluate` | Run the behavioural Decision Layer and persist a final TDS decision |
| `GET /api/v1/interviews/{id}/decision` | Fetch the final behavioural decision |
| `GET /api/v1/decisions/{id}/audit-trace` | Fetch rule hits, evidence lineage, and versions |
| `POST /api/v1/decisions/{id}/human-review` | Record audited human review / exception handling |
| `GET /api/v1/interviews/{id}/skills-assessment-summary` | Fetch the separate skills artifact |
| `POST /api/v1/skills-assessment-summaries/generate` | Generate or regenerate the Skills Assessment Summary |

### APIs to deprecate, rename, or quarantine

| Current endpoint | Confirmed evidence | Why it conflicts | Recommendation |
|---|---|---|---|
| `POST /api/v1/scoring/analyze` | `backend/app/api/scoring.py:24-180`, `documentation/API_REFERENCE.md:204-208` | It returns dual scorecards rather than a final behavioural decision plus separate skills artifact | Quarantine as internal orchestration or rename as evidence-analysis only |
| `POST /api/v1/shortlist/generate` | `backend/app/api/shortlist.py:11-18`, `documentation/API_REFERENCE.md:222-226` | It exists only to rank candidates | Deprecate |
| `GET /api/v1/interviews/{id}/score` | `backend/app/api/interviews.py:389-407` | Legacy score contract still references `overall_score` | Deprecate and replace with `/decision` |
| `POST /api/v1/interviews/{id}/scores` | `backend/app/api/interviews.py:435-481` | Manual score save path conflicts with deterministic decision policy and still references `overall_score` | Quarantine or remove |
| Role rubric endpoints | `backend/app/api/roles.py:142-173` | Keeps recruiter-editable scoring/rubric semantics alive | Replace with constrained policy-input management |

### Model Service 2 API contract changes

Confirmed evidence:
- Current response exposes `overall_score` and `outcome` (`PASS`, `REVIEW`, `FAIL`). Evidence: `model-service-2/app/schemas.py:45-55`, `model-service-2/API_README.md:179-185`.

Recommendation:
- `overall_score` should become internal-only or be renamed to an evidence-strength field that is clearly non-decisional.
- `outcome` should be removed from the public product contract.
- API language should use `Skills Assessment Summary`, not `Skills Fit Decision`.

Important implementation note:
- The current frontend and legacy interview endpoints also appear contract-misaligned because some code still expects `overall_score` on `InterviewScore`, while the ORM now stores `culture_fit_score`. Evidence: `backend/app/api/interviews.py:403`, `backend/app/api/interviews.py:449`, `backend/app/models/interview_score.py:17-22`.

## 11. Frontend UX Gap Analysis

### Current frontend concepts that conflict with TDS

| Current concept | Confirmed evidence | Conflict |
|---|---|---|
| `AI Shortlist` | `src/lib/pages/RoleDetails.jsx:150-153`, `src/lib/components/ShortlistView.jsx:29-32` | Ranking-first product framing |
| `% Match` | `src/lib/pages/RoleDetails.jsx:240-243` | Score-first comparative signal |
| `Overall Score` | `src/lib/pages/InterviewReport.jsx:346-392` | Turns internal evidence into the product output |
| `Culture Fit Score` | `documentation/USER_GUIDE.md:267`, UI score framing across interview views | Score-first language |
| `Skills Fit Score` | `documentation/USER_GUIDE.md:268`, `src/lib/pages/InterviewReport.jsx:412-449`, `src/lib/components/SkillsFitCard.jsx:56-168` | Presents skills as a decision-like outcome |
| `Override Score` | `src/lib/pages/InterviewReport.jsx:478-501` | Contradicts TDS guardrail governance |
| Ranking / candidate comparison | `src/lib/components/CandidateComparison.jsx:131-213` | TDS explicitly does not rank candidates |
| PASS / FAIL skills language | `src/lib/components/SkillsFitCard.jsx:6-14`, `src/lib/pages/RoleDetails.jsx:266-273` | Looks like a hiring recommendation |
| Candidate-facing score display | `src/lib/pages/CandidatePortal.jsx:195-200`, `src/lib/pages/CandidatePortal.jsx:282-300` | Conflicts with constrained feedback model |

### Recommended replacement UX

For the TDS decision surface:
- `Decision Outcome`
- `Proceed`
- `Proceed with Conditions`
- `Do Not Proceed`
- `Insufficient Evidence`
- `Confidence validity`
- `Integrity status`
- `Risk summary`
- `Environment fit`
- `Trade-off statement`
- `Conditions for Proceed with Conditions`
- `Human review / exception flow`

For skills:
- `Skills Assessment Summary`
- `Observed Skills Evidence`
- `Competency Coverage`
- `Skills Gaps`
- `Evidence Strength`
- `Requires Human Review`
- Separate artifact label: `This summary is not used in the behavioural TDS decision outcome.`

## 12. AS Built Document Rewrite Plan

### Confirmed evidence of conflicting AS Built language

| Current AS Built concept | Evidence | Why it must be removed or reframed |
|---|---|---|
| dual scorecard | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2061`, `:5359-5364` | Frames the product around scorecards, not decisioning |
| recruiter decision support | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2062` | Says recruiters interpret scores and rankings rather than the system resolving a decision |
| shortlist rankings | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2062`, `:3761-3765`, `:5384` | Contradicts “TDS does not rank candidates” |
| 0-100 scoring | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:4123`, `:5388` | Contradicts score-as-output language |
| scoring rubric | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:3930`, `:5359-5406` | Keeps recruiter-owned score design central |
| AI hiring recommendation | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:5406` | Needs reframing as system decision plus audited human review |
| admin override | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:3757`, `:5406`, `:5474` | Needs governance language, not free override wording |
| skills fit score | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2153`, plus current docs/UI references | Makes skills look co-decisional |
| skills outcome | Model-service-2 references in the packet and supporting docs | Produces decision-like skills language |

### Replacement language aligned to TDS

Recommendation:

| Replace this language | With this language |
|---|---|
| `dual scorecard` | `behavioural decisioning with separate behavioural and skills evidence artifacts` |
| `recruiter decision support` | `deterministic behavioural decisioning with auditable human review` |
| `shortlist rankings` | `decision outcome buckets` |
| `0-100 score` | `internal evidence scoring not shown as the primary product outcome` |
| `scoring rubric` | `decision policy inputs` or `environment policy mapping` |
| `AI hiring recommendation` | `behavioural decision outcome` |
| `admin override` | `audited human review / exception handling` |
| `skills fit score` | `Skills Assessment Summary` |
| `skills outcome` | `skills evidence summary` |

Required replacement framing for skills:
- **Skills Assessment Summary is produced as a separate organisational evidence artifact. It does not influence the MVP1 behavioural decision outcome.**

## 13. MVP Implementation Roadmap

### Recommendation

Phase 1 — TDS language freeze
- Freeze the rule that MVP1 final decisioning is behavioural only.
- Freeze the term `Skills Assessment Summary`.
- Remove ranking and score-first product language from docs and design briefs.

Phase 2 — Decision Layer module
- Add the backend Decision Layer for behavioural decisioning only, using existing behavioural classification and risk logic as the seed.

Phase 3 — decision schema additions
- Add decision outcome, decision dimension evaluation, risk, audit, and policy-version schema.

Phase 4 — skills artifact boundary
- Reframe Model Service 2 output as Skills Assessment Summary.
- Prevent it from influencing decision outcomes.

Phase 5 — model-service-1 contract cleanup
- Ensure behavioural evidence feeds the Decision Layer and that model-side recommendation fields are non-authoritative.

Phase 6 — API changes
- Add decision APIs.
- Add skills summary APIs.
- Quarantine scoring and shortlist APIs.

Phase 7 — frontend decision outcome UX
- Replace scores, rankings, and override-score concepts with decision state, confidence validity, integrity status, risk summary, and rationale.

Phase 8 — frontend skills artifact UX
- Show the Skills Assessment Summary as a separate card or report artifact with a clear exclusion notice.

Phase 9 — audit trace and governance
- Add decision traceability, policy versioning, and human review logging.

Phase 10 — AS Built rewrite
- Rewrite the AS Built and supporting docs around decisioning infrastructure rather than dual scorecards and shortlist rankings.

## 14. Files Likely To Change First

### Talenti MVP

Backend decisioning/scoring services:
- `backend/app/services/interview_scoring.py:204-418`, `:499-546`, `:651-686`
- `backend/app/api/scoring.py:24-180`
- `backend/app/api/interview_scores.py:22-100`
- `backend/app/api/interviews.py:389-547`
- `backend/app/api/shortlist.py:11-18`
- `backend/app/api/roles.py:142-173`

Schema/models:
- `backend/app/models/interview_score.py:11-47`
- `backend/app/models/score_dimension.py:10-38`
- `backend/app/models/job_role.py:10-30`
- `backend/app/models/post_hire_outcome.py:17-65`
- `backend/app/schemas/scoring.py:61-201`
- `backend/app/schemas/interviews.py:110-139`
- `backend/app/schemas/shortlist.py:4-16`
- `backend/app/schemas/roles.py:56-109`

Frontend:
- `src/lib/pages/RoleDetails.jsx:85-90`, `:150-153`, `:214-281`
- `src/lib/pages/InterviewReport.jsx:223-229`, `:263-302`, `:346-449`, `:478-501`
- `src/lib/components/ShortlistView.jsx:29-32`, `:69-114`
- `src/lib/components/CandidateComparison.jsx:131-213`
- `src/lib/components/SkillsFitCard.jsx:56-168`
- `src/lib/pages/EditRoleRubric.jsx:14-23`, `:78-124`, `:156-203`
- `src/lib/pages/NewRole.jsx:34-40`, `:120-143`, `:341-364`
- `src/lib/pages/CandidatePortal.jsx:195-200`, `:282-300`

Docs:
- `documentation/API_REFERENCE.md:204-226`
- `documentation/ARCHITECTURE_OVERVIEW.md:59-64`, `:85-90`
- `documentation/USER_GUIDE.md:211-274`
- `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2061-2062`, `:3757-3765`, `:4123`, `:5384-5406`

### Model Service 1

- `model-service-1/app/schemas.py:94-117`
- `model-service-1/app/model.py:259-311`
- `model-service-1/talenti_dimensions.py:635-714`, `:721-929`

Specific attention:
- response schemas
- final recommendation fields
- behavioural evidence output fields

### Model Service 2

- `model-service-2/app/schemas.py:45-55`
- `model-service-2/app/model.py:213-274`
- `model-service-2/model_draft.py:230-253`
- `model-service-2/API_README.md:45-53`, `:179-185`, `:203-231`
- `model-service-2/README.md:3-16`

Specific attention:
- response schemas
- outcome fields
- skills score fields
- PASS / REVIEW / FAIL fields
- any language that implies final hiring decision
- API docs and tests using decision-like language

## 15. Final Recommendation

What to build first:
- Freeze the behavioural-only MVP1 decision policy.
- Add the backend Decision Layer and final behavioural decision schema.
- Quarantine shortlist and score-first recruiter language immediately.

What not to build yet:
- Do not build composite behavioural-plus-skills decisioning.
- Do not reintroduce ranking or “best candidate” logic behind a new label.
- Do not expand candidate feedback until the decision contract is stable.

What to rename immediately:
- `AI Shortlist` -> remove
- `Overall Score` -> remove as primary UX
- `Skills Fit Score` -> `Skills Assessment Summary`
- `Override Score` -> `Human Review`
- `scoring_rubric` product language -> `decision policy inputs`

What to leave as legacy or internal evidence for now:
- behavioural internal scores,
- per-dimension score rows,
- raw model payload capture,
- environment lineage,
- post-hire outcome capture,
- skills evidence internals that can be mapped into the Skills Assessment Summary.

How to treat Model Service 2 in MVP1:
- Keep it as an evidence producer only.
- Rename and surface its outputs as a Skills Assessment Summary.
- Remove or quarantine any PASS / FAIL / REVIEW language from public product surfaces.

How to describe the Skills Assessment Summary:
- A separate organisational evidence artifact that summarises observed competencies, competency coverage, skills gaps, evidence strength, confidence, and source references.
- It is not a hiring recommendation and is not used in the behavioural TDS decision outcome.

The biggest risk if the team half-implements TDS:
- The product will present behavioural decision language on top of an unchanged dual-scorecard architecture, causing policy ambiguity, audit weakness, recruiter confusion, and a high probability that skills or ranking logic will continue to influence decisions informally even if not formally encoded.

**Model Service 2 should remain in the system as the producer of a Skills Assessment Summary, but it must be explicitly excluded from MVP1 final TDS decisioning. The behavioural Decision Layer alone owns the final TDS outcome.**
