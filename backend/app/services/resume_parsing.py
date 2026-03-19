from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    CandidateProfile,
    CandidateSkill,
    Education,
    EmploymentHistory,
    File,
    ParsedProfileSnapshot,
    User,
)
from app.services.blob_storage import download_blob_bytes, is_blob_storage_configured
from app.services.domain_events import json_dumps, json_loads

EMAIL_RE = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)


def extract_resume_text(file_record: File) -> str:
    raw_bytes = _load_file_bytes(file_record)
    suffix = Path(file_record.blob_path or "").suffix.lower()

    if suffix in {".txt", ".md", ".rtf"}:
        return raw_bytes.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_pdf_text(raw_bytes)
    if suffix == ".docx":
        return _extract_docx_text(raw_bytes)
    return raw_bytes.decode("utf-8", errors="ignore")


def parse_resume_text(raw_text: str, *, file_name: str | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    lowered = [line.lower() for line in lines]
    email = _first_match(EMAIL_RE, raw_text)
    phone = _first_match(PHONE_RE, raw_text)
    urls = URL_RE.findall(raw_text)
    linkedin_url = next((url for url in urls if "linkedin.com" in url.lower()), None)
    portfolio_url = next(
        (url for url in urls if "linkedin.com" not in url.lower()),
        None,
    )
    full_name = _guess_name(lines, email=email)
    summary = _extract_summary(lines)
    skills = _extract_skills(lines, lowered)
    employment = _extract_section_entries(lines, lowered, {"experience", "employment", "work history"})
    education = _extract_section_entries(lines, lowered, {"education", "qualifications", "study"})

    return {
        "personal": {
            "full_name": full_name,
        },
        "contact": {
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "portfolio_url": portfolio_url,
        },
        "summary": summary,
        "skills": skills,
        "employment": [
            {
                "company": _split_company_title(entry)[1],
                "title": _split_company_title(entry)[0],
                "description": entry,
            }
            for entry in employment
        ],
        "education": [
            {
                "institution": entry,
                "degree": entry,
            }
            for entry in education
        ],
        "links": [url.rstrip(".,)") for url in urls[:5]],
        "raw_text": raw_text,
        "parser_metadata": {
            "file_name": file_name,
            "line_count": len(lines),
            "parser": "heuristic_resume_parser_v1",
        },
        "confidence": {
            "full_name": 0.7 if full_name else 0.0,
            "email": 0.95 if email else 0.0,
            "phone": 0.8 if phone else 0.0,
            "skills": 0.6 if skills else 0.0,
            "employment": 0.45 if employment else 0.0,
            "education": 0.45 if education else 0.0,
        },
    }


def create_parsed_snapshot(
    db: Session,
    *,
    file_id: str,
    user_id: str | None,
    parsed: dict[str, Any],
    raw_text: str,
    source_kind: str,
) -> ParsedProfileSnapshot:
    snapshot = ParsedProfileSnapshot(
        user_id=user_id,
        file_id=file_id,
        snapshot_type="resume_parse",
        parser_version="heuristic_resume_parser_v1",
        source_kind=source_kind,
        data_json=json_dumps(parsed),
        confidence_json=json_dumps(parsed.get("confidence") or {}),
        raw_text=raw_text,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def apply_parsed_profile(
    db: Session,
    *,
    user: User,
    profile: CandidateProfile,
    parsed: dict[str, Any],
    snapshot: ParsedProfileSnapshot,
    source_kind: str,
) -> None:
    personal = parsed.get("personal") or {}
    contact = parsed.get("contact") or {}

    full_name = _clean_string(personal.get("full_name"))
    if full_name and not user.full_name:
        user.full_name = full_name

    first_name, last_name = _split_name(full_name)
    if first_name and not profile.first_name:
        profile.first_name = first_name
    if last_name and not profile.last_name:
        profile.last_name = last_name

    for profile_field, parsed_value in (
        ("email", contact.get("email")),
        ("phone", contact.get("phone")),
        ("linkedin_url", contact.get("linkedin_url")),
        ("portfolio_url", contact.get("portfolio_url")),
    ):
        cleaned = _clean_string(parsed_value)
        if cleaned and not getattr(profile, profile_field):
            setattr(profile, profile_field, cleaned)

    profile.profile_prefilled = True
    profile.profile_review_status = "needs_confirmation"
    profile.prefill_source = source_kind
    profile.parsed_snapshot_id = snapshot.id

    _upsert_skills(db, user.id, parsed.get("skills") or [])
    _upsert_employment(db, user.id, parsed.get("employment") or [])
    _upsert_education(db, user.id, parsed.get("education") or [])


def load_parsed_snapshot(snapshot: ParsedProfileSnapshot | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    parsed = json_loads(snapshot.data_json, default=None)
    return parsed if isinstance(parsed, dict) else None


def _load_file_bytes(file_record: File) -> bytes:
    blob_path = file_record.blob_path or ""
    local_path = Path(blob_path)
    if local_path.exists():
        return local_path.read_bytes()
    if is_blob_storage_configured():
        return download_blob_bytes(blob_path)
    raise ValueError(f"Unable to load file bytes for {blob_path}")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return raw_bytes.decode("utf-8", errors="ignore")
    reader = PdfReader(io.BytesIO(raw_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(raw_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        return raw_bytes.decode("utf-8", errors="ignore")
    document = Document(io.BytesIO(raw_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)


def _first_match(pattern: re.Pattern[str], raw_text: str) -> str | None:
    match = pattern.search(raw_text)
    if not match:
        return None
    return match.group(1).strip()


def _guess_name(lines: list[str], *, email: str | None) -> str | None:
    for line in lines[:5]:
        if email and email.lower() in line.lower():
            continue
        if "@" in line or "http" in line.lower():
            continue
        if len(line.split()) > 5:
            continue
        if any(char.isdigit() for char in line):
            continue
        return line
    return None


def _extract_summary(lines: list[str]) -> str | None:
    summary_lines: list[str] = []
    for line in lines[1:6]:
        lowered = line.lower()
        if any(keyword in lowered for keyword in ("skills", "experience", "education", "@", "linkedin")):
            break
        summary_lines.append(line)
    return " ".join(summary_lines[:3]) or None


def _extract_skills(lines: list[str], lowered: list[str]) -> list[str]:
    skills: list[str] = []
    collecting = False
    for original, lower in zip(lines, lowered):
        if lower in {"skills", "technical skills", "core skills"}:
            collecting = True
            continue
        if collecting and lower in {"experience", "employment", "education", "projects"}:
            break
        if collecting:
            skills.extend(_split_skill_line(original))

    if skills:
        return _dedupe_preserve_order(skills)[:20]

    for line in lines:
        if "," in line and len(line.split(",")) >= 3:
            guessed = _split_skill_line(line)
            if len(guessed) >= 3:
                return _dedupe_preserve_order(guessed)[:20]
    return []


def _split_skill_line(value: str) -> list[str]:
    parts = re.split(r"[|,/]|(?:\s{2,})", value)
    return [
        _clean_string(part)
        for part in parts
        if _clean_string(part)
        and len(_clean_string(part)) <= 40
        and _clean_string(part).lower() not in {"skills", "technical skills", "core skills"}
    ]


def _extract_section_entries(
    lines: list[str],
    lowered: list[str],
    headings: set[str],
) -> list[str]:
    results: list[str] = []
    collecting = False
    for original, lower in zip(lines, lowered):
        if lower in headings:
            collecting = True
            continue
        if collecting and lower in {"skills", "education", "experience", "employment", "projects", "references"}:
            if lower not in headings:
                break
        if collecting and original:
            results.append(original)
    return results[:5]


def _split_company_title(value: str) -> tuple[str, str]:
    for separator in (" at ", " - ", " | "):
        if separator in value.lower():
            parts = re.split(separator, value, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                return _clean_string(parts[0]) or value, _clean_string(parts[1]) or value
    return value, value


def _split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    parts = [part for part in full_name.split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _upsert_skills(db: Session, user_id: str, skills: list[str]) -> None:
    if not skills:
        return
    existing = {
        skill.skill_name.lower()
        for skill in db.query(CandidateSkill).filter(CandidateSkill.user_id == user_id).all()
    }
    for skill_name in _dedupe_preserve_order(skills)[:20]:
        cleaned = _clean_string(skill_name)
        if not cleaned or cleaned.lower() in existing:
            continue
        db.add(
            CandidateSkill(
                user_id=user_id,
                skill_name=cleaned,
                skill_type="resume_extracted",
            )
        )
        existing.add(cleaned.lower())


def _upsert_employment(db: Session, user_id: str, employment: list[dict[str, Any]]) -> None:
    if not employment:
        return
    if db.query(EmploymentHistory).filter(EmploymentHistory.user_id == user_id).count() > 0:
        return
    for entry in employment[:3]:
        title = _clean_string(entry.get("title")) or "Previous Role"
        company = _clean_string(entry.get("company")) or title
        db.add(
            EmploymentHistory(
                user_id=user_id,
                company=company,
                title=title,
                description=_clean_string(entry.get("description")),
            )
        )


def _upsert_education(db: Session, user_id: str, education: list[dict[str, Any]]) -> None:
    if not education:
        return
    if db.query(Education).filter(Education.user_id == user_id).count() > 0:
        return
    for entry in education[:2]:
        institution = _clean_string(entry.get("institution")) or "Education"
        degree = _clean_string(entry.get("degree")) or institution
        db.add(
            Education(
                user_id=user_id,
                institution=institution,
                degree=degree,
                field_of_study=_clean_string(entry.get("field_of_study")),
                grade=_clean_string(entry.get("grade")),
            )
        )


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = _clean_string(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
