# Talenti Decisioning Alignment Investigation

## Scope

Repos investigated:
- Talenti MVP (`/`)
- Model Service 1 - Cultural Fit Model (`/model-service-1`)
- Model Service 2 - Skills Fit Model (`/model-service-2`)

Key documents investigated:
- `documentation/AUDIT_PACKET_AS_BUILT.pdf` via `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html`
- `documentation/ARCHITECTURE_OVERVIEW.md`
- `documentation/ARCHITECTURE_DECISIONS.md`
- `documentation/ARCHITECTURE_DIAGRAM.md`
- `documentation/API_REFERENCE.md`
- `documentation/USER_GUIDE.md`

Assumptions and scope controls:
- No separate TDS / Talenti Decisioning System document was found in the repos. "TDS alignment" below is therefore judged against the user-provided target state plus ADR-007 and the decision-logic documents in the model-service repos.
- The PDF packet is cited through `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html` because it provides stable line references for the AS Built content.
- "Evidence inventory" below focuses on material runtime code, schema, API, contract, and UX occurrences. Repetitive test-only or README-only duplicates are omitted unless they prove a boundary or implementation fact.

## 1. Executive Summary

Verdict:
- The current system is mixed, but still primarily score/ranking oriented at the product, schema, API, documentation, and UX layers.
- There is real deterministic decision logic in the stack, but it is not a first-class end-to-end decisioning system.

Biggest alignment gaps:
- The platform still describes itself as dual scorecards and recruiter decision support, not a system that resolves a defensible final decision outcome. Evidence: `documentation/ARCHITECTURE_OVERVIEW.md:59-64`, `:85-90`; `documentation/USER_GUIDE.md:219-224`, `:252-274`; `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2041-2063`, `:5359-5406`.
- Ranking and shortlist ordering are still first-class concepts in backend and frontend, not just stale language. Evidence: `backend/app/api/shortlist.py:11-18`; `backend/app/schemas/shortlist.py:4-16`; `src/lib/pages/RoleDetails.jsx:85-90`, `:150-153`, `:214-217`, `:240-243`; `src/lib/components/ShortlistView.jsx:29-32`, `:70-97`, `:111-114`.
- Model services still own decision-like outputs instead of stopping at signal/evaluation boundaries. Evidence: `model-service-1/app/model.py:230-311`; `model-service-1/app/schemas.py:94-116`; `model-service-2/app/model.py:161-241`; `model-service-2/model_draft.py:230-245`.
- There is no first-class unified Decision Layer that combines culture evidence, skills evidence, confidence validity, risk accumulation, and final decision state across the whole product.
- The database remains score-first: `interview_scores`, `score_dimensions`, `job_roles.scoring_rubric`; there is no first-class `decision_outcomes`, `decision_state`, `decision_valid`, `confidence_gate_passed`, or `decision_audit_trail`. Evidence: `backend/alembic/versions/0001_initial.py:79`, `:223-252`; `backend/app/models/interview_score.py:11-47`; `backend/app/models/score_dimension.py:10-37`; `backend/app/models/job_role.py:25`.
- "Insufficient Evidence / No judgement possible" is not represented as a first-class outcome in backend, APIs, frontend, or schema. Search found no material implementation of `insufficient evidence`, `no judgement`, `no judgment`, `decision_state`, or `decision_outcome`.

What is already strong and worth preserving:
- Deterministic org-environment translation with lineage and confidence-driven caution cap. Evidence: `backend/app/services/org_environment.py:10-18`, `:293-308`; `backend/app/api/orgs.py:244-319`, `:333-342`, `:404-425`.
- Backend culture-fit classification and risk stacking already look like the seed of a real Decision Layer. Evidence: `backend/app/services/interview_scoring.py:204-291`, `:296-418`, `:651-659`.
- Model-service-1 has materially stronger decision logic than the rest of the stack: confidence buckets, fatal-risk override, named rules, rationale, and audit-oriented outputs. Evidence: `model-service-1/talenti_dimensions.py:635-714`, `:721-929`; `model-service-1/app/model.py:230-311`.
- Raw service payload capture, environment snapshot capture, human override, and post-hire outcome tracking are useful foundations for future auditability. Evidence: `backend/app/models/interview_score.py:35-46`; `backend/app/api/interview_scores.py:52-160`; `backend/alembic/versions/0007_post_hire_outcomes.py:1-67`.

## 2. Repository Map

| Repo | Main purpose | Key services/modules | Relevant APIs/endpoints | Relevant schema/DDL | Frontend/UI | Contracts | Score/rank/decision evidence |
|---|---|---|---|---|---|---|---|
| Talenti MVP | Orchestration, persistence, recruiter/candidate UX | `backend/app/services/interview_scoring.py`, `ml_client.py`, `org_environment.py`, `backend/app/api/*`, `src/lib/pages/*`, `src/lib/components/*` | `/api/v1/scoring/analyze`, `/api/v1/interview-scores/*`, `/api/v1/interviews/*`, `/api/v1/shortlist/generate`, `/api/roles/{role_id}/rubric`, `/api/orgs/{org_id}/environment*` | `0001_initial.py`, `0005_scoring_canonical_dimensions.py`, `0006_org_environment_inputs.py`, `0007_post_hire_outcomes.py`, `0008_dual_scorecard_columns.py`, `backend/app/models/interview_score.py`, `score_dimension.py`, `job_role.py` | Recruiter views in `RoleDetails.jsx`, `InterviewReport.jsx`, `EditRoleRubric.jsx`, `NewRole.jsx`; candidate views in `CandidatePortal.jsx`; shortlist in `ShortlistView.jsx` | `backend/app/schemas/scoring.py`, `interviews.py`, `shortlist.py`, `roles.py` | Score/rank language is primary; culture-fit recommendation logic exists but is not system-wide |
| Model Service 1 | Culture / behavioural fit extraction plus deterministic recommendation logic | `model-service-1/app/model.py`, `app/schemas.py`, `talenti_dimensions.py`, `model_draft.py` | `/predict` in `model-service-1/app/main.py` | N/A (service contract only) | No frontend | Transcript + operating environment + taxonomy in; scores/confidence/rationale/alignment/risk/recommendation out | Most "decision-dominant" part of stack, but still score-first contract |
| Model Service 2 | JD-driven skills fit scoring and must-have gating | `model-service-2/app/model.py`, `app/schemas.py`, `model_draft.py`, `jd_parser.py` | `/predict`, `/predict/transcript` in `model-service-2/app/main.py` | N/A (service contract only) | No frontend | JD + resume + answers/transcript in; `overall_score`, `outcome`, `scores`, `must_haves_*`, `gaps` out | Explicitly score-first; returns thresholded PASS/REVIEW/FAIL outcome |

## 3. Evidence Inventory: Scoring / Ranking Concepts

| Repo | File path and lines | Term/concept | What the code/doc does today | Why it conflicts with decisioning direction | Disposition |
|---|---|---|---|---|---|
| MVP docs | `documentation/USER_GUIDE.md:211-224` | `Scoring rubric`, `dual scorecard` | Explains recruiter-editable weights/thresholds and two independent scorecards | Keeps evaluation as adjustable score design rather than policy-driven decision infrastructure | Rename/reframe; constrain or remove recruiter-owned rubric logic |
| MVP docs | `documentation/USER_GUIDE.md:252-268` | `Use AI to rank candidates`, `Candidates are scored 0-100`, `Culture Fit Score`, `Skills Fit Score` | Defines shortlist ranking and score displays as recruiter workflow | Directly anchors product to ranking/score interpretation | Remove from product language; replace with outcome buckets and evidence summaries |
| MVP docs | `documentation/API_REFERENCE.md:47`, `:61`, `:189-192`, `:216-226` | `avg score`, `rubric`, `score`, `Generate ranked shortlist` | API contract is still score/rubric/shortlist centered | Codifies score-first vocabulary and client behavior | Rename over time; preserve legacy fields only as transitional inputs |
| MVP docs | `documentation/ARCHITECTURE_OVERVIEW.md:59-64`, `:88-90` | `score`, `dual-scorecard assessment`, `shortlist rankings` | Architecture overview says Talenti scores interviews and provides rankings to inform recruiter decisions | Architecture document is still describing decision support, not decision resolution | Reframe document before external sharing |
| AS Built | `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2061-2062`, `:2268`, `:2308`, `:2317-2318`, `:5359-5406` | `two independent scores`, `stores results in interview_scores and score_dimensions`, `scoring rubric`, `AI to rank candidates` | The AS Built packet mirrors the score-first model across runtime, schema, and workflow | Strong evidence that external-facing documentation still encodes old philosophy | Rewrite before sharing with Naran's team |
| MVP backend | `backend/app/api/shortlist.py:11-18` | `ranked = sorted(...)` | Explicitly sorts candidates by numeric score and returns ranked shortlist | Ranking is first-class system behavior, not incidental wording | Delete or downgrade to internal convenience only after decision buckets exist |
| MVP backend | `backend/app/schemas/shortlist.py:4-16` | `score`, `ranked` | Shortlist contract is numeric score in, ranked list out | API bakes in ordering semantics | Replace with outcome buckets or filtered candidate sets |
| MVP frontend | `src/lib/pages/RoleDetails.jsx:85-90`, `:150-153`, `:214-217`, `:240-243`, `:252-260` | `match_score`, `AI Shortlist`, `Sorted by AI Match`, `% Match`, `Interview Score` | Role page sorts applications by match score and advertises AI shortlist/ranking | Product experience is ranking-first | Replace with decision outcome states and evidence/risk cards |
| MVP frontend | `src/lib/components/ShortlistView.jsx:29-32`, `:70-97`, `:111-114` | `AI-Powered Shortlist`, `ranked by semantic match`, `Strong Match/Good Match/Potential`, `No candidates to rank yet` | UX is ranking display plus numeric match quality bands | Forces recruiter to interpret scores/ranks rather than consume resolved outcomes | Replace with outcome buckets and rationale/risk summaries |
| MVP frontend | `src/lib/pages/EditRoleRubric.jsx:14-23`, `:90-97`, `:156-181` | `Edit Scoring Rubric`, `Scoring Dimensions`, `confidence` as a dimension | Recruiters can edit dimension weights and labels, including a literal `confidence` dimension | Treats confidence as a scored trait, not a decision validity gate | Remove or radically re-scope |
| MVP frontend | `src/lib/pages/NewRole.jsx:34-40`, `:120-137`, `:341-345` | `scoringWeights`, `scoring_rubric`, `Screening Criteria` | Role creation persists recruiter-authored weights as scoring rubric | Old rubric-thinking is still in role setup flow | Replace with approved decision policy inputs if recruiter control remains at all |
| MVP frontend | `src/lib/pages/InterviewReport.jsx:86-99`, `:226-227`, `:265`, `:351`, `:380`, `:482-491` | `overall_score`, `Score Details`, `Score Breakdown by Dimension`, `Override Score` | Recruiter report is organized around score display and score override | Reinforces score interpretation as the core hiring action | Reframe around decision outcome, rationale, risk, and exception handling |
| MVP backend | `backend/app/api/interviews.py:389-407`, `:435-481`, `:484-520` | `GET /score`, `POST /scores`, `overall_score` | Legacy interview API still reads/writes `overall_score` | Shows incomplete migration and preserves score-first contract | Rename/deprecate; do not extend |
| MVP backend | `backend/app/api/orgs.py:218-229` | `avg(InterviewScore.overall_score)` | Org stats still calculate average match score via legacy field name | Confirms score metrics remain the management view | Downgrade to internal analytics at most |
| MVP schema | `backend/alembic/versions/0001_initial.py:79`, `:223-252` | `scoring_rubric`, `score_dimensions`, `interview_scores`, `overall_score` | Initial schema is explicitly score-first | Score-first foundation still shapes current data model | Replace with decision-first equivalents over time |
| MVP schema | `backend/alembic/versions/0008_dual_scorecard_columns.py:13-23` | `dual_scorecard_columns`, `skills_score`, `skills_outcome` | Renames `overall_score` to `culture_fit_score` but keeps scorecard framing | Migration is a refinement of scoring architecture, not a shift to decision architecture | Retain temporarily as legacy/internal inputs only |
| Model-service-2 | `model-service-2/app/model.py:11-16`, `:157-241`; `model-service-2/model_draft.py:1-20`, `:230-245` | `score`, `overall_score`, `Pass/Review/Fail` | Skills service computes numeric scores and thresholded final outcome | Final judgement still lives inside a model service and is score-based | Retain competency evidence; move final decision resolution out |

## 4. Evidence Inventory: Decision / Outcome Concepts

| Repo | File path and lines | What exists today | Logic type | Sufficient for TDS-style decisioning? |
|---|---|---|---|---|
| MVP backend | `backend/app/services/interview_scoring.py:204-291` | Backend classifies culture dimensions into `pass/watch/risk` using env-adjusted thresholds and a confidence gate | First-class logic | Strong seed, but only for culture dimensions |
| MVP backend | `backend/app/services/interview_scoring.py:296-418` | Backend risk stack produces `proceed/caution/reject` from dimension outcomes, fatal signals, co-fail, effective risk count, and environment confidence cap | First-class logic | Partial only; not unified across culture + skills and no no-judgement state |
| MVP backend | `backend/app/services/interview_scoring.py:651-659` | Final backend pipeline step resolves culture-fit recommendation after model calls | First-class logic | Partial; still buried inside scoring pipeline rather than a named Decision Layer |
| MVP schema | `backend/app/models/interview_score.py:24-43` | Stores `overall_alignment`, `overall_risk_level`, `recommendation`, `dimension_outcomes`, raw model payloads, env snapshot, human override | First-class persistence of some decision-like artifacts | Partial; lacks decision state, validity, confidence gate result, audit trail, insufficient evidence |
| MVP schema | `backend/app/models/score_dimension.py:22-37` | Stores per-dimension `confidence`, `outcome`, thresholds, `gap`, `matched_signals`, `source`, `rationale` | First-class persistence | Good intermediate-evaluation layer; still named as scores |
| MVP backend | `backend/app/api/interview_scores.py:52-100` | Stores human override alongside automated recommendation | First-class logic | Partial; good exception capture, but not a complete decision audit trail |
| MVP backend | `backend/app/services/org_environment.py:10-18`, `:293-308`; `backend/app/api/orgs.py:244-319`, `:333-342`, `:404-425` | Preserves question-to-variable lineage, environment confidence, extra fatal risks, reviewer flags, and recommendation cap on low-confidence environment | First-class logic | Strong and should be preserved; but applies to org environment, not full candidate decision lineage |
| Model-service-1 | `model-service-1/talenti_dimensions.py:635-714`, `:721-929` | Confidence buckets, fatal-risk override, named rules fired, rationale, dimension results, recommendation | First-class logic | Strongest TDS-like artifact in the codebase, but trapped inside one model service and still score-centric |
| Model-service-1 | `model-service-1/app/schemas.py:94-116` | Response includes `recommendation`, `overall_alignment`, `overall_risk_level`, `dimension_outcomes`, `env_requirements` | First-class contract | Better than the rest of the system, but still not a final platform decision contract |
| Model-service-2 | `model-service-2/app/model.py:213-241`; `model-service-2/model_draft.py:230-245` | Skills service applies hard rules and emits `PASS/REVIEW/FAIL` | First-class logic | Insufficient and boundary-breaking; this should become intermediate evaluation, not final service-owned outcome |
| Docs only | Search across repos | No material runtime representation of `insufficient evidence`, `no judgement`, `decision_state`, `decision_valid`, `confidence_gate_passed`, `priority_dimension_failures`, `decision_audit_trail` | Missing | No |

## 5. Current End-to-End Flow

Current flow:

```text
Candidate profile / CV / application
  -> Talenti MVP frontend and candidate APIs
  -> backend persists candidate/application/role/interview state
  -> org environment questionnaire persists operating environment + lineage
  -> interview transcript segments stored
  -> interview complete event enqueues scoring_run
  -> backend loads transcript + role + org context
  -> backend calls model-service-1 (/predict)
  -> backend calls model-service-2 (/predict/transcript)
  -> backend extracts culture scores
  -> backend classifies culture dimensions (pass/watch/risk)
  -> backend computes culture recommendation (proceed/caution/reject)
  -> backend extracts skills scorecard (overall_score + PASS/REVIEW/FAIL)
  -> backend stores interview_scores + score_dimensions + raw payloads
  -> recruiter UI shows scorecards, interview score, skills fit, shortlist/ranking views
```

Evidence:
- Interview completion enqueues scoring: `backend/app/api/interviews.py:204-265`.
- Model-service fan-out: `backend/app/services/ml_client.py:214-260`.
- Synchronous scoring endpoint mirrors same model orchestration: `backend/app/api/scoring.py:118-179`.
- Auto-scoring pipeline and persistence: `backend/app/services/interview_scoring.py:588-686`, `:499-583`.

What input data is collected:
- Candidate profile, CV/resume, applications, skills, employment, education: `src/api/candidates.js:3-92`, `documentation/API_REFERENCE.md:71-135`.
- Job description, requirements, `scoring_rubric`: `src/lib/pages/NewRole.jsx:108-143`; `backend/alembic/versions/0001_initial.py:78-80`.
- Org operating environment answers and derived signals: `backend/app/api/orgs.py:233-319`, `:322-476`.
- Interview transcript segments and anti-cheat signals: `backend/app/api/interviews.py:204-265`, `:323-386`.

What each model service returns:
- Model-service-1: per-dimension scores, confidence, rationale, overall alignment, risk level, recommendation, dimension outcomes, env requirements. Evidence: `model-service-1/app/schemas.py:94-116`, `model-service-1/app/model.py:301-311`.
- Model-service-2: `overall_score`, `outcome`, per-competency scores, must-have pass/fail, gaps, summary. Evidence: `model-service-2/app/schemas.py:45-56`, `model-service-2/app/model.py:231-241`.

Where cultural fit and skills fit are combined:
- They are orchestrated in the Talenti MVP backend, but not resolved into one final decision. Evidence: `backend/app/api/scoring.py:118-179`; `backend/app/services/interview_scoring.py:651-661`.

Where confidence is calculated or displayed:
- Calculated in model-service-1 and model-service-2: `model-service-1/app/model.py:172-217`; `model-service-2/app/model.py:181-190`.
- Persisted in `score_dimensions`: `backend/app/models/score_dimension.py:22-32`.
- Used as a gate for culture-fit dimension classification and environment caution cap: `backend/app/services/interview_scoring.py:247-256`, `:401-408`; `backend/app/api/orgs.py:404-425`.
- Not surfaced as a strong recruiter-facing decision validity concept in the frontend.

Where risks are calculated or displayed:
- Culture risk stack: `backend/app/services/interview_scoring.py:296-418`.
- Org-environment fatal risks: `backend/app/services/org_environment.py:304-305`, `:357-360`; `backend/app/api/orgs.py:287-289`, `:418-475`.
- Frontend largely shows scores, not structured risk reasoning; the main visible "risk" badge in the report page is anti-cheat risk, not decision risk. Evidence: `src/lib/pages/InterviewReport.jsx:125-139`, `:451-473`.

Where scores are stored:
- `interview_scores`: `backend/app/models/interview_score.py:11-47`.
- `score_dimensions`: `backend/app/models/score_dimension.py:10-37`.

Where ranking or sorting happens:
- Shortlist API sorts numerically: `backend/app/api/shortlist.py:11-18`.
- Role page sorts applications by `match_score`: `src/lib/pages/RoleDetails.jsx:85-90`.

What the frontend ultimately displays:
- Role page: AI match, interview score, skills fit, shortlist CTA. Evidence: `src/lib/pages/RoleDetails.jsx:150-169`, `:214-243`, `:251-282`.
- Interview report: overall score, score details, skills fit, override score. Evidence: `src/lib/pages/InterviewReport.jsx:223-229`, `:263-289`, `:346-392`, `:412-449`, `:478-501`.
- Shortlist view: ranked candidates by semantic match. Evidence: `src/lib/components/ShortlistView.jsx:29-32`, `:70-80`, `:95-114`.

Whether there is any explicit decision resolution step:
- Yes, but only for culture fit, inside backend scoring orchestration.
- No, for a final platform-wide outcome that resolves culture evidence + skills evidence + validity + insufficient evidence + risk accumulation into one enforceable decision state.

## 6. Decision Layer Gap Analysis

Is there a first-class Decision Layer / Engine / Service today?
- No separate, first-class decision layer exists across the platform.

What exists instead:
- A proto decision layer lives inside `backend/app/services/interview_scoring.py`, specifically `classify_dimensions()` and `compute_risk_stack()` (`:204-418`).
- Model-service-1 also contains its own recommendation engine in `model-service-1/talenti_dimensions.py:721-929`.
- Model-service-2 contains its own thresholded outcome engine in `model-service-2/model_draft.py:230-245`.

Why this is not sufficient:
- The logic is scattered across three places.
- The backend only resolves a culture-fit recommendation.
- Skills fit remains an adjacent scorecard with `PASS/REVIEW/FAIL`, not an input into one final Talenti outcome.
- Nothing produces a single authoritative `decision_state` with structured rationale and lineage.

Which repo is acting as the current orchestration layer:
- Talenti MVP backend. Evidence: `backend/app/api/scoring.py:118-179`; `backend/app/services/interview_scoring.py:588-686`; `backend/app/services/ml_client.py:214-260`.

Conceptual recommendation:
- The Decision Layer should live in the Talenti MVP backend, not in either model service.
- It should receive:
  - raw/normalized model outputs
  - org decision policy
  - confidence summaries
  - identified risk flags
  - priority-dimension definitions
  - evidence sufficiency status
- It should produce:
  - final decision state
  - decision validity
  - structured rationale
  - rule hits
  - priority-dimension failures
  - risk accumulation summary
  - audit lineage

Logic that should move into that layer:
- Final outcome resolution across culture + skills.
- Confidence-as-validity gating.
- Insufficient evidence / no judgement handling.
- Priority-dimension failure logic.
- Unified risk accumulation.
- Recruiter exception handling with auditable override semantics.

## 7. Model Service Boundary Analysis

### Model Service 1 - Cultural Fit

Current responsibilities:
- Ingest transcript plus org environment and taxonomy.
- Score the five canonical culture dimensions.
- Compute confidence and rationale per dimension.
- Compute dimension outcomes, overall alignment, risk level, and recommendation.

Input contract:
- `transcript`, optional ids, `operating_environment`, `taxonomy`, `trace`. Evidence: `model-service-1/app/schemas.py:46-56`.

Output contract:
- `scores`, `summary`, `metadata`, `model_version`, `overall_alignment`, `overall_risk_level`, `recommendation`, `dimension_outcomes`, `env_requirements`. Evidence: `model-service-1/app/schemas.py:94-116`.

What it returns:
- Scores: yes.
- Signals/evidence: indirectly via rationale and underlying trace.
- Confidence: yes.
- Risks: yes.
- Rationale: yes.
- Decisions: yes, `recommendation`.

Boundary assessment:
- Too wide. It is doing more than signal extraction or even dimension evaluation.
- It is already making final-like judgment calls that the platform should own centrally.

### Model Service 2 - Skills Fit

Current responsibilities:
- Parse JD into expectations.
- Score role-specific competencies from resume + interview text.
- Apply must-have gating and threshold rules.
- Emit `overall_score`, `PASS/REVIEW/FAIL`, gaps, and must-have results.

Input contract:
- `job_description`, `resume_text`, transcript or interview answers, optional `role_title`, `seniority`. Evidence: `model-service-2/app/schemas.py:16-33`.

Output contract:
- `overall_score`, `outcome`, `scores`, `must_haves_passed`, `must_haves_failed`, `gaps`, `summary`, `metadata`, `model_version`. Evidence: `model-service-2/app/schemas.py:45-56`.

What it returns:
- Scores: yes.
- Signals/evidence: partial.
- Confidence: yes.
- Risks: not as a first-class risk model.
- Rationale: yes.
- Decisions: yes, `PASS/REVIEW/FAIL`.

Boundary assessment:
- Clearly too wide for the desired TDS boundary.
- The service is making thresholded outcome judgments that should become intermediate evaluations or policy inputs.

Recommended target boundary:

| Responsibility | Should live where |
|---|---|
| Signal extraction | Model services |
| Dimension / competency evaluation | Model services, if treated as intermediate evidence objects |
| Confidence calculation | Model services produce evidence confidence; Decision Layer decides whether that confidence is sufficient for validity |
| Risk identification | Mixed: model services may flag candidate-specific risks, but final risk accumulation should be in Decision Layer |
| Final decision resolution | Decision Layer only |

## 8. Database / DDL / Schema Findings

| Existing table/model | Current purpose | Score-first or decision-first? | Alignment issue | Suggested future equivalent |
|---|---|---|---|---|
| `job_roles.scoring_rubric` (`backend/alembic/versions/0001_initial.py:79`, `backend/app/models/job_role.py:25`) | Recruiter-configurable scoring weights | Score-first | Encodes rubric-thinking and recruiter-owned evaluation logic | `decision_policy_inputs` or constrained role-policy config |
| `interview_scores` (`backend/app/models/interview_score.py:11-47`) | Summary record per interview | Mixed but still score-first | Main record is still scorecard-oriented; recommendation is appended, not authoritative decision state | `decision_outcomes` |
| `score_dimensions` (`backend/app/models/score_dimension.py:10-37`) | Per-dimension score/evaluation record | Mixed | Useful intermediate layer, but naming remains score-centric | `decision_evaluations` or `signal_dimension_evaluations` |
| `org_environment_inputs` (`backend/alembic/versions/0006_org_environment_inputs.py:13-31`) | Org questionnaire answers, signals, derived environment, fatal risks | Decision-supporting | Good lineage for org policy context, but not candidate decision lineage | Retain |
| `post_hire_outcomes` (`backend/alembic/versions/0007_post_hire_outcomes.py:14-67`) | Post-hire validation snapshots | Outcome-oriented | Useful, but linked to `interview_scores` rather than a real decision entity | Link to future `decision_outcomes` |
| `audit_log` (`backend/alembic/versions/0001_initial.py:296-315`) | Generic audit log | Generic audit | Not a decision audit trail; no rule-lineage or outcome-specific structure | `decision_audit_trail` plus generic audit log |
| `applications` (`backend/app/models/application.py:10-26`) | Candidate role application state | Neutral | Frontend/docs assume `match_score`, but current model does not define it | If kept, score fields should not drive ordering; use decision bucket/status instead |
| `invitations.expires_at` (`backend/alembic/versions/0001_initial.py:255-271`) | Recruiter-controlled invitation expiry | Workflow control | May not align with Talenti-controlled workflow policy | Constrained policy-driven invite expiry |

Schema capability assessment:

| Desired capability | Current status |
|---|---|
| `decision_state` | Missing |
| `decision_valid` | Missing |
| `confidence_gate_passed` | Missing |
| `priority_dimension_failures` | Missing |
| `risk_accumulation_score` | Missing as first-class field; only partial via `overall_risk_level` |
| Structured rationale | Partial via `summary`, per-dimension `rationale`, raw payloads |
| Signal -> dimension -> rule -> outcome lineage | Partial only; org environment lineage exists, final decision lineage does not |
| Decision audit trail | Partial only; generic `audit_log` and human override exist |
| `insufficient_evidence` / `no_judgement` outcome | Missing |

Important contradiction:
- The AS Built packet still documents stale `interview_scores` and `score_dimensions` shapes centered on `overall_score`, `narrative_summary`, `candidate_feedback`, `weight`, and quoted evidence: `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:4118-4145`.
- The current ORM/migrations have already diverged, but only into a richer scorecard model, not a true decision schema. Evidence: `backend/app/models/interview_score.py:17-43`; `backend/alembic/versions/0005_scoring_canonical_dimensions.py:12-104`; `backend/alembic/versions/0008_dual_scorecard_columns.py:13-23`.

## 9. API Contract Findings

| Endpoint | Current request/response | Decisioning support | What likely needs to change |
|---|---|---|---|
| `POST /api/v1/scoring/analyze` (`backend/app/api/scoring.py:28-179`) | Takes transcript plus optional rubric/JD/org context; returns `culture_fit` and `skills_fit` scorecards | Partial only | Should return raw model outputs and/or intermediate evaluations plus a unified final decision outcome from a Decision Layer |
| `GET /api/v1/interviews/{id}/score` (`backend/app/api/interviews.py:389-407`) | Returns legacy `overall_score`, `summary`, `recommendation` | Weak | Deprecate in favor of `GET /decision` or richer `interview-score` contract |
| `GET /api/v1/interviews/{id}/dimensions` (`backend/app/api/interviews.py:410-432`) | Returns score-dimension list | Partial | Could survive as intermediate evaluation endpoint if renamed/reframed |
| `POST /api/v1/interviews/{id}/scores` (`backend/app/api/interviews.py:435-481`) | Legacy save/update of `overall_score` and dimensions | No | Remove or quarantine as legacy admin tooling |
| `GET /api/v1/interviews/{id}/report` (`backend/app/api/interviews.py:484-547`) | Returns interview + score + dimensions + transcripts | Partial | Should return decision outcome, rationale, risk summary, validity, and lineage snapshot |
| `PATCH /api/v1/interview-scores/{score_id}` (`backend/app/api/interview_scores.py:22-49`) | Updates culture-fit score, summary, recommendation | Weak | Recast as controlled correction of intermediate evaluation or decision metadata, not manual score editing |
| `POST /api/v1/interview-scores/{score_id}/override` (`backend/app/api/interview_scores.py:52-100`) | Sets human override decision + reason | Partial | Keep concept, but convert to auditable exception handling against a decision entity |
| `POST /api/v1/interview-scores/{score_id}/outcomes` (`backend/app/api/interview_scores.py:103-160`) | Records post-hire outcomes | Good foundation | Retarget to future decision entity for calibration/audit |
| `POST /api/v1/shortlist/generate` (`backend/app/api/shortlist.py:11-18`) | Numeric candidate list in, ranked candidate list out | No | Replace with bucket generation or filterable decision outcome grouping |
| `PATCH /api/roles/{role_id}/rubric` (`documentation/API_REFERENCE.md:61`; `backend/app/api/roles.py:153-168`) | Updates recruiter-controlled scoring rubric | Misaligned | Replace with tightly constrained policy input management only if product explicitly allows it |
| `POST /api/orgs/{org_id}/environment*` (`backend/app/api/orgs.py:233-476`) | Sets org environment and confidence | Strong input-side support | Keep; use as one input into a formal decision policy |
| `PATCH /api/orgs/{organisation_id}/retention` (`backend/app/api/orgs.py:162-187`) | Recruiter/org-controlled recording retention | Product-policy question | Needs explicit product decision on Talenti-owned vs recruiter-owned controls |

Contract-level conclusion:
- The public API still exposes scorecards, rankings, and editable scoring/rubric concepts more strongly than it exposes decision outcomes.
- No public API currently exposes a first-class final decision state with validity, insufficient evidence, structured rationale, and lineage.

## 10. Frontend / UX / Language Findings

| File | Component/screen | Current UX behavior | Alignment issue | Suggested replacement |
|---|---|---|---|---|
| `src/lib/pages/RoleDetails.jsx:85-90`, `:150-169`, `:214-243`, `:251-282` | Role details / candidates list | Sorts by `match_score`, shows `AI Shortlist`, `% Match`, `Interview Score`, `Skills Fit` | Ranking/score-first recruiter workflow | Replace with decision buckets, decision state badges, rationale/risk highlights |
| `src/lib/components/ShortlistView.jsx:29-32`, `:70-97`, `:111-114` | Shortlist view | Displays ranked candidates by match with score bands | Directly contradicts "outcomes not rankings" | Replace with outcome groups such as Proceed / Proceed with conditions / Do Not Proceed / Insufficient Evidence |
| `src/lib/pages/EditRoleRubric.jsx:14-23`, `:90-97`, `:156-181` | Edit scoring rubric | Lets recruiter edit dimension weights; includes `confidence` as a scored dimension | Confidence should be a validity gate, not a scored trait | Replace with approved decision policy configuration only if allowed |
| `src/lib/pages/NewRole.jsx:34-40`, `:120-143`, `:341-345` | New role setup | Persists `scoring_rubric` and "Screening Criteria" weights | Old rubric-thinking at role creation time | Reframe as policy inputs or approved role template selection |
| `src/lib/pages/InterviewReport.jsx:223-229`, `:263-289`, `:346-392`, `:412-449`, `:478-501` | Interview report | Organized around score details, overall score, and score override | Makes scores the main mental model | Replace with decision outcome, decision validity, risk summary, rationale, and exception handling |
| `src/lib/components/CandidateComparison.jsx:131-175` | Candidate comparison | Compares `Overall Score` and `Skills Fit` to highlight highest-scoring candidate | Encourages cross-candidate ranking rather than candidate-by-policy resolution | Replace with decision evidence comparison only if needed |
| `src/lib/pages/CandidatePortal.jsx:65-69`, `:97-123`, `:168-220` | Candidate portal | Candidate portal, practice interview, applications, and score display are implemented | Useful to know for scope; not just future-state docs | Keep if in product scope; otherwise clarify MVP vs future state |
| `src/lib/components/SendInvitationDialog.jsx:73-79` | Invitation send dialog | Promises `7-day expiration period` | Workflow control is recruiter-facing/configurable language | Decide whether expiry is Talenti-owned policy |
| `src/lib/components/ResumeBatchUploadDialog.jsx:137-159`, `:184-187` | Bulk resume upload | Implements recruiter review queue and invite prep with `expires_in_days: 7` | Strongly implemented; not just documented | Keep if valid, but separate from decisioning claims |

## 11. AS Built Document Alignment

Overall judgment:
- The AS Built packet is still substantially aligned to the old philosophy: "score -> display -> let recruiter decide."
- It is not honest yet to describe the platform as a full Talenti Decisioning System.

Classification of the major workflow/document claims:

| AS Built item | Current classification | Evidence |
|---|---|---|
| Candidates set up profiles | Current MVP reality | `src/lib/pages/CandidatePortal.jsx:101-145`; `src/api/candidates.js:3-14` |
| Candidates upload CVs/resumes | Current MVP reality | `src/api/candidates.js:81-90`; `documentation/API_REFERENCE.md:81-83`; bulk flow in `src/lib/components/ResumeBatchUploadDialog.jsx:79-121` |
| Practice interviews | Current MVP reality | `src/lib/pages/CandidatePortal.jsx:224-249`; `src/api/candidates.js:60-71` |
| Recruiters add company values for culture scoring | Still valid but needs new language | Docs say "company values"; code actually uses operating-environment questionnaire and taxonomy: `documentation/USER_GUIDE.md:184`; `backend/app/api/orgs.py:233-319` |
| Recruiters edit rubric / dimension weights / thresholds | Current MVP reality and old thinking to remove/constrain | `src/lib/pages/EditRoleRubric.jsx:78-125`; `documentation/USER_GUIDE.md:211-217` |
| Recruiters set invitation expiration | Current MVP reality, but policy ownership unresolved | `documentation/USER_GUIDE.md:233`; `src/lib/components/SendInvitationDialog.jsx:73-79`; `backend/alembic/versions/0001_initial.py:255-271` |
| Bulk resume upload | Current MVP reality | `src/lib/components/ResumeBatchUploadDialog.jsx:79-172`; `documentation/API_REFERENCE.md:138-150` |
| Generate shortlist / use AI to rank candidates | Current MVP reality and product-positioning risk | `backend/app/api/shortlist.py:11-18`; `src/lib/components/ShortlistView.jsx:29-32`; `documentation/USER_GUIDE.md:252-258` |
| Candidates are scored 0-100 | Current MVP reality and old thinking to remove | `documentation/USER_GUIDE.md:256`; `src/lib/pages/InterviewReport.jsx:351-380`; `model-service-2/app/schemas.py:47-49` |
| Culture Fit Score / Skills Fit Score | Current MVP reality but needs new language | `documentation/USER_GUIDE.md:267-268`; `src/lib/pages/InterviewReport.jsx:415-446` |
| AI hiring recommendation | Current MVP reality but high positioning risk | `backend/app/models/interview_score.py:27-33`; `documentation/USER_GUIDE.md:274` |
| Admin override of AI recommendation | Current MVP reality but should become human review/exception handling with audit trail | `backend/app/api/interview_scores.py:52-100`; `src/lib/pages/InterviewReport.jsx:478-501` |

Key contradiction:
- ADR-007 claims "decision-dominant scoring logic", but that truth only partially survives into the product. It is strongest in model-service-1 and backend culture-fit risk stacking, weak in skills, absent as a unified decision contract, absent in schema, and not dominant in UX.

## AS Built Packet: TDS Misalignment Findings

### Top 20 AS Built statements that conflict with TDS direction

| # | AS Built statement or claim | Classification | Why it conflicts |
|---|---|---|---|
| 1 | Talenti enables organisations to `score` and report on candidate interviews (`...rendered.html:2041`) | Old thinking to remove | Frames platform as scoring system |
| 2 | `Automated dual-scorecard assessment` (`:2045`) | Retain only as historical/current-state description | Anchors architecture around scorecards, not outcomes |
| 3 | Every interview produces `two independent scores` (`:2061`) | Still technically true but misframed | A TDS needs a final resolved outcome, not only parallel scores |
| 4 | Recruiters receive `scores, risk flags, confidence levels, and shortlist rankings to inform (not replace) hiring decisions` (`:2062`) | Real implemented behavior and product-positioning risk | Explicitly says recruiter interprets outputs rather than system resolving outcome |
| 5 | Model-service-1 output includes per-dimension scores and recommendation (`:2153`) | Partially true but boundary problem | Model service owns decision-like outputs |
| 6 | Model-service-2 output includes `overall score` and `PASS/REVIEW/FAIL` (`:2161`) | Real implemented behavior and boundary problem | Skills service owns thresholded judgments |
| 7 | Runtime scoring flow stores into `interview_scores` and `score_dimensions` (`:2268`) | Real implemented behavior | Still a scoring pipeline, not decision-outcome pipeline |
| 8 | `job_roles` includes `scoring rubric` (`:2308`) | Real implemented behavior | Rubric-thinking remains first-class |
| 9 | `interview_scores` is a `Scoring summary per interview` (`:2317`) | Real implemented behavior | Core entity is still score-first |
| 10 | `score_dimensions` are `Per-dimension scores` (`:2318`) | Real implemented behavior | Intermediate evaluation entity remains score-oriented |
| 11 | ADR-007: `all scoring decisions are made by deterministic rules` (`:2588`) | Partially true | Deterministic rules exist, but not as a unified platform decision layer |
| 12 | `Update scoring rubric for a role` (`:3643`) | Real implemented behavior | Recruiter-edited scoring remains official platform behavior |
| 13 | AS Built schema for `interview_scores` centered on `overall_score` (`:4118-4123`) | Documentation stale and score-first | Both stale and philosophically wrong for TDS |
| 14 | AS Built schema for `score_dimensions` centered on individual dimension scores (`:4136-4144`) | Documentation stale and score-first | No decision lineage or policy resolution |
| 15 | `Add company values (used for culture fit scoring)` (`:5317`) | Needs reframe | Culture evidence should be tied to approved policy inputs, not generic scoring language |
| 16 | `dual scorecard` (`:5359-5364`) | Retain only as current-state description | Conflicts with need for final outcome |
| 17 | `Set expiration (default 7 days)` (`:5370`) | Product-policy question | May incorrectly imply recruiter-owned workflow control |
| 18 | `Use AI to rank candidates` (`:5384`) | Remove before external sharing | Directly conflicts with anti-ranking direction |
| 19 | `Candidates are scored 0-100` (`:5388`) | Remove before external sharing | Directly conflicts with outcome-state framing |
| 20 | `Culture Fit Score`, `Skills Fit Score`, `Admins can override the AI hiring recommendation` (`:5397-5406`) | Retain only after reframing | Must become decision evidence + exception handling language |

### Top 20 code/doc areas likely responsible for those statements

| # | Code/doc area | Why it drives the AS Built wording |
|---|---|---|
| 1 | `documentation/USER_GUIDE.md:211-274` | Mirrors score/rank/override workflow language |
| 2 | `documentation/API_REFERENCE.md:47-61`, `:189-226` | API reference codifies score/rubric/shortlist model |
| 3 | `documentation/ARCHITECTURE_OVERVIEW.md:59-90`, `:868-888` | Official architecture story remains scorecard-based |
| 4 | `backend/alembic/versions/0001_initial.py:79`, `:223-252` | Core schema names are score-first |
| 5 | `backend/app/models/job_role.py:25` | `scoring_rubric` remains persisted |
| 6 | `backend/app/models/interview_score.py:17-27` | `culture_fit_score`, `skills_score`, `recommendation` on same entity |
| 7 | `backend/app/models/score_dimension.py:16-29` | Per-dimension score store remains canonical |
| 8 | `backend/app/api/scoring.py:28-179` | Public endpoint is literally `scoring/analyze` |
| 9 | `backend/app/services/interview_scoring.py:499-516` | Persistence function says "Persist the dual scorecard" |
| 10 | `backend/app/api/shortlist.py:11-18` | Backend implements numeric ranking |
| 11 | `backend/app/schemas/shortlist.py:4-16` | Ranked shortlist contract |
| 12 | `src/lib/pages/RoleDetails.jsx:85-90`, `:150-153`, `:214-243` | Recruiter role page centers AI match and shortlist |
| 13 | `src/lib/components/ShortlistView.jsx:29-97` | Ranking-specific shortlist presentation |
| 14 | `src/lib/pages/EditRoleRubric.jsx:14-23`, `:156-181` | Recruiter edits scoring dimensions/weights |
| 15 | `src/lib/pages/NewRole.jsx:34-40`, `:120-143` | Role creation stores scoring rubric |
| 16 | `src/lib/pages/InterviewReport.jsx:223-229`, `:346-392`, `:478-501` | Interview report and human action are score-centric |
| 17 | `model-service-1/app/schemas.py:94-116` | Culture service still foregrounds scores |
| 18 | `model-service-2/app/schemas.py:45-56` | Skills service is explicitly overall-score-driven |
| 19 | `model-service-2/model_draft.py:11-20`, `:230-245` | Model-service-2 decision logic is still score-threshold logic |
| 20 | `backend/app/api/interviews.py:389-520` | Legacy interview score endpoints keep `overall_score` alive |

### Which statements are documentation-only vs implemented

Documentation-only or stale:
- AS Built `interview_scores`/`score_dimensions` table descriptions at `:4118-4144` are stale relative to current ORM/migrations.
- Some legacy `overall_score` assumptions in docs are no longer fully accurate technically.

Reflect real implemented behavior:
- Dual scorecards, rubric editing, shortlist ranking, 0-100 scoring, human override, and recruiter-facing ranking/score UX are all materially implemented.

Should be removed before sharing externally:
- `Use AI to rank candidates`
- `Candidates are scored 0-100`
- Any wording that implies Talenti merely informs recruiter judgment with rankings and scores

Should be retained but reframed:
- Culture and skills assessment exist, but as decision evidence rather than productized scorecards
- Human override exists, but should be described as audited exception handling
- Confidence and risk exist, but should be framed as validity/risk gating, not passive display fields

Require architectural change before they can be honestly rewritten:
- Any claim that Talenti produces a final defensible decision outcome
- Any claim that confidence gates are enforced across the full system
- Any claim that risk accumulation and audit lineage are first-class across API, DB, and UX
- Any claim that insufficient evidence / no judgement is supported

## 12. TDS Alignment

Important note:
- No separate TDS document was found in the repos.
- This section therefore compares the codebase against the TDS concepts described in the request plus ADR-007.

| TDS concept | Status | Evidence / gap |
|---|---|---|
| Show observed signals | Partial | Org environment lineage exists; culture matched signals are stored; full candidate decision lineage is not first-class. Evidence: `backend/app/models/score_dimension.py:31-37`; `backend/app/api/orgs.py:274-317` |
| Confidence as a decision validity gate | Partial | Culture-fit risk downgrade and low-environment-confidence caution cap exist. Evidence: `backend/app/services/interview_scoring.py:247-256`, `:401-408` |
| Manage conflicting signals and edge cases | Partial | Model-service-1 has rule ordering, co-fail, fatal-risk handling, confidence buckets. Evidence: `model-service-1/talenti_dimensions.py:757-929` |
| Flag risk, not just positive fit | Partial | Culture side does this; skills side is still mostly pass/fail score logic | 
| Produce decision outcomes, not rankings | Missing/contradicted | Ranking remains first-class in API and UX |
| Audit-grade explainability | Partial | Raw payload capture and some rationale exist, but no unified decision lineage or decision audit trail |
| Insufficient Evidence / No Judgement | Missing | No first-class representation found |
| Model services do not own final decision logic | Contradicted | Both model services emit decision-like outputs |
| First-class Decision Layer | Missing | Backend has proto logic only |
| Decision outputs include triggering dimensions, failures, confidence issues, risk accumulation | Partial | Culture side has some of this, but not as final cross-system contract |

Changes likely required for real TDS alignment:
- Data model changes: yes.
- API changes: yes.
- Frontend changes: yes.
- Model service contract changes: yes.

## 13. Required Future Decision Schema

Investigation-based target shape:

```json
{
  "decision_id": "uuid",
  "candidate_id": "uuid",
  "role_id": "uuid",
  "organisation_id": "uuid",
  "decision_state": "PROCEED | PROCEED_WITH_CONDITIONS | DO_NOT_PROCEED | INSUFFICIENT_EVIDENCE",
  "decision_valid": true,
  "confidence_gate_passed": true,
  "confidence_summary": {
    "overall_confidence_band": "high | medium | low",
    "low_confidence_areas": ["ownership"],
    "confidence_failure_reasons": []
  },
  "observed_signals": [
    {
      "source": "model_service_1 | model_service_2 | org_environment",
      "signal_id": "ownership_accountability",
      "signal_strength": "strong | medium | weak",
      "confidence": 0.82,
      "evidence_refs": ["transcript:seg_14"]
    }
  ],
  "dimension_evaluations": [
    {
      "dimension": "ownership",
      "evaluation_state": "pass | watch | risk",
      "required_pass": 60,
      "required_watch": 45,
      "actual_score": 58,
      "gap": -2,
      "triggering_signals": ["ownership_accountability"],
      "rationale": "Below pass threshold but not fatally weak."
    }
  ],
  "priority_dimension_failures": ["ownership"],
  "risk_flags": [
    {
      "risk_code": "ambiguity_ownership_cofail",
      "severity": "high",
      "source": "decision_layer"
    }
  ],
  "risk_accumulation": {
    "risk_level": "low | medium | high",
    "effective_risk_count": 2,
    "fatal_override_triggered": false
  },
  "decision_rationale": {
    "internal_rationale": "Structured machine-readable explanation.",
    "human_facing_rationale": "Candidate should not proceed because..."
  },
  "insufficient_evidence_reasons": [],
  "model_outputs_used": {
    "culture_fit": {"model_version": "2.0.0"},
    "skills_fit": {"model_version": "3.0.0"}
  },
  "rule_version": "decision-rules-v1",
  "decision_policy_version": "org-policy-v3",
  "audit_trace": {
    "signals_to_dimensions": [],
    "dimensions_to_rules": [],
    "rules_to_outcome": [],
    "created_by": "system",
    "created_at": "2026-04-24T00:00:00Z"
  }
}
```

Required separation of concerns:
- Raw model outputs: scores, signals, evidence, confidence, must-have findings, raw summaries.
- Intermediate evaluations: dimension outcomes, competency evaluations, policy threshold comparisons, risk flags.
- Final decision outcome: single `decision_state`, `decision_valid`, and structured rationale.
- Human-facing rationale: simple narrative generated from the structured decision.
- Audit/trace data: signal -> dimension -> rule -> outcome lineage, versions, timestamps, override records.

## 14. Risk Register

| Risk | Evidence | Severity | Recommended mitigation |
|---|---|---|---|
| Product positioning risk | Docs/UI still say scores, rankings, recruiter interpretation: `documentation/USER_GUIDE.md:219-274`; `src/lib/components/ShortlistView.jsx:29-97` | High | Reframe language immediately; do not present ranking as primary value proposition |
| Technical architecture risk | No first-class Decision Layer; logic scattered across backend and both model services | High | Define and centralize Decision Layer in MVP backend |
| Data model risk | Core entities are still `interview_scores`, `score_dimensions`, `scoring_rubric` | High | Introduce decision-first schema and demote legacy score entities |
| Explainability risk | Partial rationale exists, but no full lineage from signals to final outcome | High | Add structured lineage and rule-hit persistence |
| Auditability risk | Generic audit log exists, but no decision-specific audit trail or validity flag | High | Add `decision_audit_trail`, policy versions, override trail |
| UX language risk | Recruiters are shown ranked lists, match percentages, and score overrides | High | Replace with decision buckets and rationale/risk presentation |
| Model/service boundary risk | Both model services emit outcome/recommendation-like judgments | Medium-High | Narrow model service outputs to evidence/evaluation objects |
| Future rebuild risk | Legacy `overall_score` remnants and frontend/backend mismatches signal partial migration | Medium-High | Stop extending legacy contracts; isolate and retire them deliberately |

## 15. Prioritised Recommendations

### Phase 1 - Language and conceptual alignment

- Remove or downgrade score/rank language in docs and UI first.
- Reframe AS Built packet from "dual scorecards and recruiter decision support" to "decision evidence feeding a decision layer".
- Change recruiter-facing labels such as `AI Shortlist`, `% Match`, `Overall Score`, `Override Score`, `Use AI to rank candidates`.

### Phase 2 - Decision Layer specification

- Define a named Decision Engine / Decision Layer in the MVP backend.
- Define canonical final states:
  - Proceed
  - Proceed with conditions
  - Do Not Proceed
  - Insufficient Evidence / No judgement possible
- Define what counts as:
  - confidence gate failure
  - priority-dimension failure
  - risk accumulation
  - insufficient evidence

### Phase 3 - Data model and API alignment

- Add decision-first storage for decision outcomes and audit trail.
- Preserve score artifacts only as internal intermediate inputs where needed.
- Replace or deprecate score-first API contracts and ranking endpoints.

### Phase 4 - UX alignment

- Replace ranking/score-first recruiter views with outcome buckets.
- Surface rationale, confidence validity, risks, and missing evidence instead of raw scores as the primary UX.
- Move human override to auditable exception handling.

### Phase 5 - Audit and defensibility

- Persist signal -> dimension -> rule -> outcome lineage.
- Version decision policy and rule sets.
- Add reporting structures that are defensible without requiring recruiters to reverse-engineer scores.

## 16. Open Questions for Product / TDS

- What are the exact final decision states?
- Is `Proceed with conditions` distinct from `Caution`, or is it the replacement label?
- What exact conditions make a decision invalid versus merely weak?
- What exact confidence thresholds should block a final decision?
- Which dimensions are "priority dimensions" and are they org-specific or Talenti-controlled?
- How should culture evidence and skills evidence combine into a single final outcome?
- What risk accumulation logic is desired across culture + skills + integrity + environment uncertainty?
- Is `Insufficient Evidence / No judgement possible` required in MVP or later?
- Which controls remain recruiter-owned versus Talenti-owned?
- Can recruiters still change role policy inputs, or only select approved templates?
- Are invitation expiry and retention policy product-owned or recruiter-configurable?
- Is candidate portal functionality in MVP scope, or future-state only?
- Are practice interviews in scope as a core product capability or a side capability?
- Is bulk resume upload core MVP?
- Can recruiters override decisions, and if so, under what audit and authorization rules?
- Are rankings being removed entirely, or merely hidden from UX while retained internally?

## 17. Final Answer

### What the current system appears to be

A hybrid system where the deepest logic is moving toward deterministic decisioning, but the product still behaves and describes itself mainly as a dual-scorecard, shortlist-ranking, recruiter-interpretation platform.

### What it needs to become

A first-class decisioning platform in which model services produce evidence, the MVP backend owns final decision resolution, and the product surfaces outcome states, validity, rationale, risk, and insufficient-evidence handling instead of rankings and editable score rubrics.

### The most important architectural gap

There is no single authoritative Decision Layer that resolves culture evidence, skills evidence, confidence validity, risk accumulation, and policy rules into one auditable final decision state.

### The top 10 concrete code/doc areas to change first

1. `documentation/generated/AUDIT_PACKET_AS_BUILT.rendered.html:2061-2062`, `:2268`, `:5359-5406`
2. `documentation/USER_GUIDE.md:211-274`
3. `documentation/API_REFERENCE.md:47-61`, `:189-226`
4. `documentation/ARCHITECTURE_OVERVIEW.md:59-90`, `:868-888`
5. `backend/app/services/interview_scoring.py:204-418`, `:651-659`
6. `backend/app/api/shortlist.py:11-18` and `backend/app/schemas/shortlist.py:4-16`
7. `backend/app/models/interview_score.py:11-47` and `backend/app/models/score_dimension.py:10-37`
8. `backend/app/models/job_role.py:25` and `backend/app/api/roles.py:153-168`
9. `src/lib/pages/RoleDetails.jsx:85-90`, `:150-169`, `:214-243`; `src/lib/components/ShortlistView.jsx:29-97`
10. `model-service-2/app/model.py:161-241` and `model-service-2/model_draft.py:230-245`

