"""
jd_parser.py — Regex-based job description parser (backend copy).

Extracts competency expectations from raw JD text. This is a standalone
copy of the parser used by model-service-2, with embedded dataclasses
so it has no external dependencies beyond the stdlib.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Domain model (duplicated from model_draft.py for backend independence)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class JobExpectation:
    competency: str
    level: str  # "must" | "nice"
    min_years: float = 0.0
    keywords: Tuple[str, ...] = ()
    threshold: float = 0.65


@dataclass
class JobProfile:
    role_title: str
    seniority: str  # "junior" | "mid" | "senior"
    expectations: List[JobExpectation]
    weights: Dict[str, float] = field(default_factory=lambda: {
        "resume": 0.40,
        "interview": 0.50,
        "experience_years": 0.10,
    })
    decision_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "pass": 75.0,
        "review": 60.0,
        "fail": 0.0,
    })
    hard_fail_min_must_pass_rate: float = 0.70


# ---------------------------------------------------------------------------
# Competency families — 10 families from spec
# ---------------------------------------------------------------------------

COMPETENCY_FAMILIES: Dict[str, Dict] = {
    "python": {
        "keywords": ("python", "fastapi", "django", "flask", "pandas", "pytest", "pip", "poetry"),
        "detection_patterns": [
            re.compile(r"\bpython\b", re.IGNORECASE),
            re.compile(r"\b(?:fastapi|django|flask)\b", re.IGNORECASE),
        ],
    },
    "machine_learning": {
        "keywords": ("machine learning", "ml", "pytorch", "tensorflow", "scikit-learn",
                      "model training", "deep learning", "neural network"),
        "detection_patterns": [
            re.compile(r"\bmachine\s+learning\b", re.IGNORECASE),
            re.compile(r"\b(?:pytorch|tensorflow|scikit[ -]learn)\b", re.IGNORECASE),
            re.compile(r"\bdeep\s+learning\b", re.IGNORECASE),
            re.compile(r"\bml\b", re.IGNORECASE),
        ],
    },
    "llm": {
        "keywords": ("llm", "large language model", "gpt", "fine-tuning", "prompt engineering",
                      "openai", "langchain", "transformers"),
        "detection_patterns": [
            re.compile(r"\bllm(?:s)?\b", re.IGNORECASE),
            re.compile(r"\blarge\s+language\s+model", re.IGNORECASE),
            re.compile(r"\b(?:gpt|openai|langchain|fine[ -]?tun)", re.IGNORECASE),
            re.compile(r"\bprompt\s+engineering\b", re.IGNORECASE),
        ],
    },
    "speech": {
        "keywords": ("speech", "speech-to-text", "stt", "whisper", "asr",
                      "automatic speech recognition", "voice", "transcription"),
        "detection_patterns": [
            re.compile(r"\bspeech[ -]?to[ -]?text\b", re.IGNORECASE),
            re.compile(r"\b(?:whisper|asr)\b", re.IGNORECASE),
            re.compile(r"\bautomatic\s+speech\s+recognition\b", re.IGNORECASE),
            re.compile(r"\btranscription\b", re.IGNORECASE),
        ],
    },
    "azure": {
        "keywords": ("azure", "app service", "azure functions", "cognitive search",
                      "rbac", "azure devops", "azure ml", "blob storage"),
        "detection_patterns": [
            re.compile(r"\bazure\b", re.IGNORECASE),
            re.compile(r"\bapp\s+service\b", re.IGNORECASE),
        ],
    },
    "aws": {
        "keywords": ("aws", "amazon web services", "s3", "lambda", "sagemaker",
                      "ec2", "ecs", "dynamodb", "cloudformation"),
        "detection_patterns": [
            re.compile(r"\baws\b", re.IGNORECASE),
            re.compile(r"\bamazon\s+web\s+services\b", re.IGNORECASE),
            re.compile(r"\b(?:sagemaker|lambda|ec2|ecs|s3)\b", re.IGNORECASE),
        ],
    },
    "mlops": {
        "keywords": ("mlops", "ml ops", "ci/cd", "docker", "kubernetes", "mlflow",
                      "model deployment", "model monitoring", "containerisation"),
        "detection_patterns": [
            re.compile(r"\bmlops\b", re.IGNORECASE),
            re.compile(r"\bml\s+ops\b", re.IGNORECASE),
            re.compile(r"\b(?:docker|kubernetes|k8s|mlflow)\b", re.IGNORECASE),
            re.compile(r"\bmodel\s+(?:deployment|monitoring)\b", re.IGNORECASE),
        ],
    },
    "system_design": {
        "keywords": ("system design", "architecture", "scalability", "distributed systems",
                      "microservices", "api design", "trade-offs", "observability"),
        "detection_patterns": [
            re.compile(r"\bsystem\s+design\b", re.IGNORECASE),
            re.compile(r"\b(?:architecture|scalability|microservice)", re.IGNORECASE),
            re.compile(r"\bdistributed\s+system", re.IGNORECASE),
            re.compile(r"\bapi\s+design\b", re.IGNORECASE),
        ],
    },
    "rag": {
        "keywords": ("rag", "retrieval augmented generation", "vector", "embedding",
                      "retrieval", "cognitive search", "vector database", "semantic search"),
        "detection_patterns": [
            re.compile(r"\brag\b", re.IGNORECASE),
            re.compile(r"\bretrieval[\s-]+augmented", re.IGNORECASE),
            re.compile(r"\bvector\s+(?:database|store|search)\b", re.IGNORECASE),
            re.compile(r"\bsemantic\s+search\b", re.IGNORECASE),
            re.compile(r"\bembedding", re.IGNORECASE),
        ],
    },
    "fullstack": {
        "keywords": ("fullstack", "full-stack", "frontend", "backend", "react", "next.js",
                      "node.js", "javascript", "typescript", "html", "css"),
        "detection_patterns": [
            re.compile(r"\bfull[ -]?stack\b", re.IGNORECASE),
            re.compile(r"\b(?:react|next\.?js|node\.?js|angular|vue)\b", re.IGNORECASE),
            re.compile(r"\b(?:javascript|typescript)\b", re.IGNORECASE),
        ],
    },
}

# ---------------------------------------------------------------------------
# Must vs nice classification
# ---------------------------------------------------------------------------

_MUST_PATTERNS = [
    re.compile(r"\b(?:required|essential|must[ -]have|mandatory|critical|necessary)\b", re.IGNORECASE),
]
_NICE_PATTERNS = [
    re.compile(r"\b(?:preferred|nice[ -]to[ -]have|bonus|desirable|advantageous|ideal(?:ly)?|plus)\b", re.IGNORECASE),
]

_YEARS_PATTERN = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def _classify_level(text: str, match_start: int, match_end: int) -> str:
    window_size = 200
    window = text[max(0, match_start - window_size): match_end + window_size]
    nice_score = sum(1 for p in _NICE_PATTERNS if p.search(window))
    must_score = sum(1 for p in _MUST_PATTERNS if p.search(window))
    if nice_score > must_score:
        return "nice"
    return "must"


def _extract_min_years(text: str, match_start: int, match_end: int) -> float:
    window_size = 150
    window = text[max(0, match_start - window_size): match_end + window_size]
    m = _YEARS_PATTERN.search(window)
    if m:
        return float(m.group(1))
    return 0.0


# ---------------------------------------------------------------------------
# Seniority detection
# ---------------------------------------------------------------------------

_SENIORITY_PATTERNS = [
    (re.compile(r"\b(?:senior|sr\.?|lead|principal|staff)\b", re.IGNORECASE), "senior"),
    (re.compile(r"\b(?:junior|jr\.?|graduate|entry[ -]level|intern)\b", re.IGNORECASE), "junior"),
    (re.compile(r"\b(?:mid(?:dle)?[ -]?(?:level)?|intermediate)\b", re.IGNORECASE), "mid"),
]


def detect_seniority(text: str) -> str:
    for pattern, level in _SENIORITY_PATTERNS:
        if pattern.search(text):
            return level
    return "mid"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_job_description(jd_text: str, role_title: str = "") -> JobProfile:
    """
    Parse a raw job description into a structured JobProfile.
    """
    combined_text = f"{role_title} {jd_text}" if role_title else jd_text
    seniority = detect_seniority(combined_text)

    expectations: List[JobExpectation] = []

    for family_name, family in COMPETENCY_FAMILIES.items():
        best_match_start = None
        best_match_end = None
        matched = False

        for pattern in family["detection_patterns"]:
            m = pattern.search(jd_text)
            if m:
                matched = True
                if best_match_start is None or m.start() < best_match_start:
                    best_match_start = m.start()
                    best_match_end = m.end()

        if not matched:
            continue

        level = _classify_level(jd_text, best_match_start, best_match_end)
        min_years = _extract_min_years(jd_text, best_match_start, best_match_end)
        threshold = 0.70 if level == "must" else 0.60

        expectations.append(JobExpectation(
            competency=family_name,
            level=level,
            min_years=min_years,
            keywords=family["keywords"],
            threshold=threshold,
        ))

    return JobProfile(
        role_title=role_title or "Unspecified Role",
        seniority=seniority,
        expectations=expectations,
    )
