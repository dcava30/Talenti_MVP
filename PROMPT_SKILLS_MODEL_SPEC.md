# Talenti Skills Model (Model Service 2) — Full Specification

## Context

Talenti has a **dual scorecard** architecture. Two independent model services score candidates in parallel — their results are never merged or averaged:

| | Model Service 1 (Culture Fit) | Model Service 2 (Skills Fit) |
|---|---|---|
| **Purpose** | Behavioural alignment to org operating environment | Technical/functional competency against job requirements |
| **Dimensions** | Fixed 5 canonical (ownership, execution, challenge, ambiguity, feedback) | Dynamic, JD-driven, role-specific (e.g. python, azure, rag, system_design) |
| **Score range** | 0–100 per dimension | 0–1 per competency (normalised) |
| **Response fields** | recommendation, dimension_outcomes, env_requirements | overall_score, outcome, must_haves_passed/failed, gaps, per-competency scores |
| **Input** | transcript + taxonomy + operating_environment | job_description + resume_text + interview_answers |

Model Service 2 is the **skills model**. It takes a job description, parses it into structured competency expectations, then scores a candidate's resume and interview answers against those expectations. The dimension set is not fixed — it is derived from the JD for each role.

The backend calls both services from `POST /api/v1/scoring/analyze` and returns a response with two top-level objects: `culture_fit` and `skills_fit`. The database stores them as separate columns (`culture_fit_score`, `skills_score`) and preserves the raw responses from each service (`service1_raw`, `service2_raw`).

---

## Part 1: UI — Skills Requirements Gathering

### 1.1 Role Creation Flow (existing: `src/lib/pages/NewRole.jsx`)

When a recruiter creates a new role, they fill in:
- **title** (required) — e.g. "Senior ML Engineer"
- **department** — dropdown (Engineering, Product, Design, etc.)
- **work_type** — remote / hybrid / onsite
- **location** — free text
- **salary_range_min / salary_range_max** — integers
- **description** (required) — the full job description, pasted or typed as free text

On submission the role is saved to `job_roles` with status `draft`. The `description` field holds the raw JD text. The `requirements` JSONB column stores AI-extracted structured requirements (skills, experience, qualifications, responsibilities).

### 1.2 Skills Requirements Extraction (new/enhanced)

After the JD is saved, the system should parse it to extract structured competency expectations. This is the bridge between what the recruiter writes and what model-service-2 scores against.

**Step 1 — Automatic JD Parsing**

When a role is created or the JD is updated, the backend should call the JD parser (`jd_parser.py :: parse_job_description()`) to produce a `JobProfile`:

```
JobProfile:
  role_title: str           — extracted or overridden by recruiter
  seniority: str            — junior | mid | senior (detected from JD text)
  expectations: List[JobExpectation]
```

Each `JobExpectation` is:
```
JobExpectation:
  competency: str           — e.g. "python", "azure", "rag", "system_design"
  level: str                — "must" | "nice" (must-have vs nice-to-have)
  min_years: float          — minimum years of experience (0.0 if not specified)
  keywords: Tuple[str, ...] — canonical keywords used for matching
  threshold: float          — minimum signal score to pass (0.70 for must, 0.60 for nice)
```

The JD parser currently recognises these competency families:
- python, machine_learning, llm, speech, azure, aws, mlops, system_design, rag, fullstack

This list should be extensible — the parser uses regex pattern matching and keyword dictionaries per competency, so new competency families can be added without changing the scoring engine.

**Step 2 — Recruiter Review & Edit UI**

After parsing, the extracted expectations should be presented to the recruiter for review and adjustment. This is a **new UI step** in the role creation/edit flow.

**Page: Edit Role Skills Requirements** (`/roles/:roleId/skills` or embedded in role edit)

Display a card for each extracted competency:

```
┌─────────────────────────────────────────────────────┐
│  Python                                    [must ▾] │
│                                                     │
│  Keywords: python, fastapi, pandas, pytest          │
│  Min years: 2.0          Threshold: 0.70            │
│                                                     │
│  [Edit Keywords]  [Remove]                          │
├─────────────────────────────────────────────────────┤
│  Azure                                    [must ▾]  │
│  Keywords: azure, app service, functions, cosmos db │
│  Min years: 1.0          Threshold: 0.65            │
│                                                     │
│  [Edit Keywords]  [Remove]                          │
├─────────────────────────────────────────────────────┤
│  RAG                                      [nice ▾]  │
│  Keywords: rag, vector, embedding, retrieval        │
│  Min years: 0.0          Threshold: 0.60            │
│                                                     │
│  [Edit Keywords]  [Remove]                          │
└─────────────────────────────────────────────────────┘

[+ Add Competency]        [Re-parse from JD]     [Save]
```

**Interactions:**
- **Level toggle**: Dropdown to switch between `must` and `nice`
- **Edit Keywords**: Inline edit to add/remove keywords the scorer matches against
- **Min years**: Editable number input — how many years of experience are required
- **Threshold**: Editable slider (0.50–1.00) — the minimum match signal to consider this competency "passed"
- **Remove**: Delete a competency from the set
- **Add Competency**: Manually add a competency not detected by the parser (free-text name + keywords)
- **Re-parse from JD**: Re-run the parser on the current JD text and reset the expectations
- **Save**: Persist the final expectations to `job_roles.requirements` as structured JSON

**Storage format** (`job_roles.requirements` JSONB):

```json
{
  "skills": ["Python", "Azure", "RAG"],
  "experience": ["2+ years Python", "1+ years Azure"],
  "qualifications": ["BSc Computer Science or equivalent"],
  "responsibilities": ["Build and deploy ML pipelines", "..."],
  "job_profile": {
    "role_title": "Senior ML Engineer",
    "seniority": "senior",
    "expectations": [
      {
        "competency": "python",
        "level": "must",
        "min_years": 2.0,
        "keywords": ["python", "fastapi", "pandas", "pytest"],
        "threshold": 0.70
      },
      {
        "competency": "azure",
        "level": "must",
        "min_years": 1.0,
        "keywords": ["azure", "app service", "functions", "cosmos db"],
        "threshold": 0.65
      },
      {
        "competency": "rag",
        "level": "nice",
        "min_years": 0.0,
        "keywords": ["rag", "vector", "embedding", "retrieval"],
        "threshold": 0.60
      }
    ],
    "weights": {
      "resume": 0.40,
      "interview": 0.50,
      "experience_years": 0.10
    },
    "decision_thresholds": {
      "pass": 75.0,
      "review": 60.0,
      "fail": 0.0
    }
  }
}
```

The `job_profile` sub-object is the exact structure model-service-2 needs to score candidates. When scoring is triggered, the backend can either:
- Send the raw JD text and let model-service-2 parse it on the fly (current approach)
- Send the pre-parsed `job_profile` directly (optimised approach — avoids re-parsing)

### 1.3 Scoring Weights (existing: `src/lib/pages/EditRoleRubric.jsx`)

The existing rubric editor lets recruiters set weights for display-level dimensions (Technical Skills 20%, Domain Knowledge 15%, etc.). These are **presentation weights** used in the UI for aggregated views and are separate from the model-level competency scoring.

The skills model's internal scoring weights (`resume: 0.40, interview: 0.50, experience_years: 0.10`) control how evidence from different sources is blended per competency. These could optionally be exposed in the UI as an advanced setting, but the defaults are sensible.

---

## Part 2: Model Service 2 — Scoring Engine

### 2.1 Architecture

```
                    ┌─────────────────┐
                    │  Job Description │  (raw text from recruiter)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   JD Parser     │  jd_parser.py
                    │                 │  Regex-based extraction
                    │  Extracts:      │  → competency families
                    │  - competencies │  → must/nice classification
                    │  - levels       │  → years requirements
                    │  - keywords     │  → keyword dictionaries
                    │  - seniority    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   JobProfile    │  Structured expectations
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
     │  Resume Text  │ │Interview │ │  Years      │
     │               │ │ Answers  │ │  Heuristic  │
     │  Keyword      │ │          │ │             │
     │  matching     │ │ Keyword  │ │ Regex-based │
     │  (+ optional  │ │ matching │ │ experience  │
     │   ML layer)   │ │ (+ opt   │ │ detection   │
     │               │ │  ML)     │ │             │
     │  Weight: 0.40 │ │  W: 0.50 │ │  W: 0.10   │
     └───────┬───────┘ └────┬─────┘ └──────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Per-Competency │
                    │  Score (0–1)    │
                    │                 │
                    │  + Evidence     │
                    │  + Matched      │
                    │    keywords     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Decision Rules │
                    │                 │
                    │  Must-have pass │
                    │  rate >= 70%?   │
                    │                 │
                    │  Overall score  │
                    │  vs thresholds  │
                    │  (75/60/0)      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ScoreBreakdown │
                    │                 │
                    │  overall_score  │  0–100
                    │  outcome        │  PASS | REVIEW | FAIL
                    │  competency_    │  {competency: 0–1}
                    │    scores       │
                    │  must_haves_    │  [passed competencies]
                    │    passed       │
                    │  must_haves_    │  [failed competencies]
                    │    failed       │
                    │  gaps           │  [human-readable gap descriptions]
                    │  evidence       │  [{source, competency, signal, matched_terms}]
                    └─────────────────┘
```

### 2.2 Inputs

Model-service-2 exposes two endpoints:

**`POST /predict`** — Q&A format (primary)
```json
{
  "job_description": "Full JD text...",
  "resume_text": "Candidate resume text...",
  "interview_answers": {
    "q1": "I have 5 years of Python experience building FastAPI services...",
    "q2": "I designed a RAG pipeline with chunking and vector search...",
    "q3": "For Azure, I deployed to App Service with managed identity..."
  },
  "role_title": "Senior ML Engineer",
  "seniority": "senior"
}
```

**`POST /predict/transcript`** — Transcript format (alternative)
```json
{
  "job_description": "Full JD text...",
  "resume_text": "Candidate resume text...",
  "transcript": [
    {"speaker": "interviewer", "content": "Tell me about your Python experience."},
    {"speaker": "candidate", "content": "I've been writing Python for 5 years..."},
    {"speaker": "interviewer", "content": "How would you design a RAG system?"},
    {"speaker": "candidate", "content": "I'd start with document chunking..."}
  ],
  "role_title": "Senior ML Engineer",
  "seniority": "senior"
}
```

The transcript endpoint extracts candidate turns and converts them to indexed Q&A pairs before feeding into the same scoring pipeline.

### 2.3 Scoring Logic

For each competency extracted from the JD:

1. **Keyword matching** (`keyword_signal()`) — deterministic, uses the competency's keyword dictionary. Matches against both resume text and interview text separately. Uses a saturating logistic curve to prevent keyword stuffing:
   - 0 hits → 0.00
   - 1 hit → ~0.55
   - 2 hits → ~0.76
   - 3 hits → ~0.86

2. **ML classification** (optional, `CompetencyClassifier`) — TF-IDF + LogisticRegression, deterministic with fixed random_state. Trained per competency on labelled resume/interview snippets. Currently `classifier=None` (keyword-only mode). Placeholder for when labelled training data is available.

3. **Years heuristic** (`estimate_years_experience()`) — regex-based, looks for "X years" patterns near competency keywords in the resume. Returns the highest detected value.

4. **Blended score per competency** (0–1):
   ```
   score = (0.40 * max(keyword_resume, ml_resume) +
            0.50 * max(keyword_interview, ml_interview) +
            0.10 * min(1.0, years_detected / min_years_required)) / 1.00
   ```

5. **Pass/fail per competency**:
   - A competency passes if `score >= threshold AND years >= min_years`
   - Must-haves that fail go into `must_haves_failed` and `gaps`

6. **Overall decision**:
   - If must-have pass rate < 70% → **FAIL** (hard rule, regardless of overall score)
   - Else if overall score >= 75 → **PASS**
   - Else if overall score >= 60 → **REVIEW**
   - Else → **FAIL**

### 2.4 Output

**`PredictResponse`**:
```json
{
  "overall_score": 72.5,
  "outcome": "REVIEW",
  "scores": {
    "python": {
      "score": 0.85,
      "confidence": 0.95,
      "rationale": "Strong competency demonstrated. Meets must requirement.",
      "years_detected": 5.0,
      "matched_keywords": ["python", "fastapi", "pytest"]
    },
    "azure": {
      "score": 0.62,
      "confidence": 0.72,
      "rationale": "Adequate competency level. Nice-to-have partially met.",
      "years_detected": 1.5,
      "matched_keywords": ["azure", "app service"]
    },
    "rag": {
      "score": 0.78,
      "confidence": 0.88,
      "rationale": "Strong competency demonstrated. Meets must requirement.",
      "years_detected": 1.0,
      "matched_keywords": ["rag", "vector", "embedding", "retrieval"]
    }
  },
  "must_haves_passed": ["python", "rag"],
  "must_haves_failed": ["azure"],
  "gaps": [
    "Must-have not met: azure (score=0.62, years=1.5/2.0)"
  ],
  "summary": "Candidate shows potential but requires further evaluation for Senior ML Engineer (senior level). Overall score: 72.5/100. Strong competencies: python, rag. Areas needing development: azure.",
  "metadata": {
    "num_competencies": 3,
    "num_must_haves": 3,
    "num_evidence_items": 6,
    "processing_time_ms": 45,
    "role_title": "Senior ML Engineer",
    "seniority": "senior"
  },
  "model_version": "1.0.0"
}
```

### 2.5 Schema Definitions

```python
class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=1)        # Normalised 0–1
    confidence: float = Field(..., ge=0, le=1)
    rationale: str
    years_detected: float = 0.0
    matched_keywords: List[str] = []

class PredictResponse(BaseModel):
    overall_score: float                          # 0–100
    outcome: str                                  # PASS | REVIEW | FAIL
    scores: Dict[str, DimensionScore]             # competency → score (dynamic keys)
    must_haves_passed: List[str] = []
    must_haves_failed: List[str] = []
    gaps: List[str] = []
    summary: str
    metadata: Dict = {}
    model_version: str
```

Key difference from model-service-1: the `scores` dict keys are **dynamic** — they are whatever competencies the JD parser extracted. There is no fixed dimension set. A Python developer role might have `{python, system_design, testing}` while a data scientist role might have `{python, machine_learning, statistics, sql}`.

---

## Part 3: UI — Skills Fit Results Display

### 3.1 Interview Report — Skills Tab

The existing `InterviewReport.jsx` shows scoring results in a tabbed layout. The Skills Fit section should display:

**Skills Fit Card:**
```
┌─────────────────────────────────────────────────────────────┐
│  Skills Fit                                                 │
│                                                             │
│  Overall: 72.5 / 100                          [REVIEW]      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░              │
│                                                             │
│  Must-Haves: 2/3 passed                                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ python        ████████████████████░░░  0.85  [PASS] │    │
│  │ 5.0 yrs detected (2.0 required)                    │    │
│  │ Matched: python, fastapi, pytest                    │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ rag           ███████████████████░░░  0.78  [PASS]  │    │
│  │ 1.0 yrs detected (1.0 required)                    │    │
│  │ Matched: rag, vector, embedding, retrieval          │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ azure         ███████████████░░░░░░░  0.62  [FAIL]  │    │
│  │ 1.5 yrs detected (2.0 required)                    │    │
│  │ Matched: azure, app service                         │    │
│  │ Gap: Must-have not met (years shortfall)            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Gaps:                                                      │
│  - Must-have not met: azure (score=0.62, years=1.5/2.0)   │
│                                                             │
│  Summary: Candidate shows potential but requires further    │
│  evaluation for Senior ML Engineer (senior level).          │
└─────────────────────────────────────────────────────────────┘
```

**Key display rules:**
- Competencies are ordered: must-haves first (failed ones at top), then nice-to-haves
- Score bar colour: green (>= threshold), amber (within 0.10 of threshold), red (below threshold - 0.10)
- Years detected vs required shown for each competency
- Matched keywords shown as tags/chips
- Gaps section only shown if there are gaps
- Outcome badge: green PASS, amber REVIEW, red FAIL

### 3.2 Candidate Comparison — Skills Columns

The existing `CandidateComparison.jsx` does side-by-side comparison. For skills fit, it should show:

- Overall skills score per candidate
- Per-competency score bars (only for competencies from that role's JD)
- Must-have pass/fail counts
- Highlight the highest scorer per competency across candidates

### 3.3 Role Details — Candidate List

The existing `RoleDetails.jsx` shows a candidate list with scores. Each candidate row should show:
- Culture fit score (from model-service-1)
- Skills fit score (from model-service-2)
- Skills outcome badge (PASS / REVIEW / FAIL)
- Number of must-haves passed / total

---

## Part 4: Backend Integration

### 4.1 Scoring Flow

When `POST /api/v1/scoring/analyze` is called:

1. Backend receives transcript + interview context
2. Backend loads the role's `job_profile` from `job_roles.requirements`
3. Backend calls model-service-1 with transcript + taxonomy + operating_environment → `culture_fit`
4. Backend calls model-service-2 with job_description + resume_text + interview_answers → `skills_fit`
5. Backend combines both into `ScoringResponse` with separate `culture_fit` and `skills_fit` sections
6. Backend persists to `interview_scores` table:
   - `culture_fit_score` = culture_fit.overall_score
   - `skills_score` = skills_fit.overall_score
   - `skills_outcome` = skills_fit.outcome
   - `service1_raw` = full model-service-1 response JSON
   - `service2_raw` = full model-service-2 response JSON

### 4.2 ML Client Integration (`ml_client.py`)

The ML client calls model-service-2 at `POST http://model-service-2:8002/predict/transcript` with:

```python
payload = {
    "job_description": job_description,    # raw JD text from job_roles.description
    "resume_text": resume_text,            # from candidate application
    "transcript": transcript_segments,     # from interview
    "role_title": role_title,              # from job_roles.title
    "seniority": seniority                 # from job_roles or detected
}
```

The response is mapped into the `skills_fit` section of `ScoringResponse`:
```python
skills_fit = {
    "overall_score": response["overall_score"],
    "outcome": response["outcome"],
    "skills": {
        competency: {
            "score": int(dim["score"] * 100),  # convert 0–1 to 0–100 for display
            "confidence": dim["confidence"],
            "rationale": dim["rationale"],
            "years_detected": dim["years_detected"],
            "matched_keywords": dim["matched_keywords"]
        }
        for competency, dim in response["scores"].items()
    },
    "must_haves_passed": response["must_haves_passed"],
    "must_haves_failed": response["must_haves_failed"],
    "gaps": response["gaps"],
    "summary": response["summary"]
}
```

### 4.3 Docker Configuration

Model-service-2 runs on port **8002** (model-service-1 runs on 8001).

```yaml
# docker-compose.yml
model-service-2:
  build:
    context: ./model-service-2
    dockerfile: Dockerfile
  ports:
    - "8002:8002"
  environment:
    - LOG_LEVEL=info
    - PYTHONUNBUFFERED=1
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8002/health').read()"]
    interval: 30s
    timeout: 10s
    start_period: 40s
    retries: 3
```

### 4.4 Required Files in `model-service-2/`

```
model-service-2/
├── app/
│   ├── __init__.py          # __version__
│   ├── main.py              # FastAPI app, /predict and /predict/transcript endpoints
│   ├── model.py             # ModelPredictor wrapper — imports from model_draft + jd_parser
│   └── schemas.py           # Pydantic models (PredictRequest, PredictResponse, DimensionScore)
├── models/                  # Future: trained classifier weights
│   └── .gitkeep
├── tests/
│   ├── test_api.py
│   ├── test_model.py
│   └── test_jd_parser.py
├── model_draft.py           # Core scoring engine (DeterministicInterviewScorer, JobProfile, etc.)
├── jd_parser.py             # JD text → JobProfile parser
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Part 5: Key Design Decisions

1. **Dynamic dimensions are the point.** Model-service-2's value is that competencies are extracted from each JD. A Python role gets scored on Python, Azure, RAG. A product manager role gets scored on stakeholder management, analytics, roadmapping. The dimension set is never fixed.

2. **The JD parser is the source of truth for dimensions.** If the parser doesn't extract a competency, it doesn't get scored. Recruiters can override by editing the extracted expectations in the UI.

3. **Scores are 0–1 per competency, 0–100 overall.** This is intentionally different from model-service-1 (which uses 0–100 per dimension). The backend converts 0–1 to 0–100 for display when needed.

4. **Must-have hard fail rule.** If less than 70% of must-have competencies pass, the candidate gets FAIL regardless of overall score. This prevents a candidate who is strong in nice-to-haves but missing critical requirements from getting a PASS.

5. **Evidence is stored and auditable.** Every score is backed by specific keyword matches and source (resume vs interview). Recruiters can see exactly what evidence drove each competency score.

6. **ML classifier is optional.** The system works today with keyword matching only (`classifier=None`). When labelled training data becomes available (20–50 examples per competency), the `CompetencyClassifier` (TF-IDF + LogisticRegression) can be trained and plugged in without changing the scoring pipeline or API contract. The ML signal is blended with keyword signals via `max()`.

7. **No operating_environment input.** That's model-service-1's domain. Model-service-2 takes job_description + resume + interview_answers. The two services have deliberately different input contracts.
