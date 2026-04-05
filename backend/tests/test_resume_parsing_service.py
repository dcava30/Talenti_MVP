import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

from conftest import backend_root, clear_app_modules, prepare_test_environment, reset_database_with_migrations


def _load_resume_module():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    clear_app_modules()
    import app.services.resume_parsing as resume_parsing

    importlib.reload(resume_parsing)
    return resume_parsing


def test_parse_resume_text_extracts_contact_summary_and_sections() -> None:
    resume_parsing = _load_resume_module()
    raw_text = """
    Ada Lovelace
    ada@example.com
    +61 400 000 111
    https://linkedin.com/in/adalovelace
    https://portfolio.example.com
    Product-minded engineer with strong ownership.
    Skills
    Python, FastAPI, SQL, Docker
    Experience
    Senior Engineer at Talenti
    Education
    BSc Computer Science
    """

    parsed = resume_parsing.parse_resume_text(raw_text, file_name="resume.txt")
    assert parsed["personal"]["full_name"] == "Ada Lovelace"
    assert parsed["contact"]["email"] == "ada@example.com"
    assert parsed["contact"]["linkedin_url"].startswith("https://linkedin.com")
    assert "Python" in parsed["skills"]
    assert parsed["employment"][0]["title"] == "Senior Engineer"
    assert parsed["education"][0]["institution"] == "BSc Computer Science"
    assert parsed["parser_metadata"]["file_name"] == "resume.txt"


def test_extract_resume_text_and_load_file_bytes_local() -> None:
    resume_parsing = _load_resume_module()
    from app.models import File

    test_dir = backend_root() / ".tmp-tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    resume_file = test_dir / "resume.txt"
    resume_file.write_text("Jane Candidate\nSkills\nPython, SQL", encoding="utf-8")

    try:
        file_record = File(blob_path=str(resume_file), purpose="candidate_cv")
        text = resume_parsing.extract_resume_text(file_record)
        assert "Jane Candidate" in text
    finally:
        if resume_file.exists():
            resume_file.unlink()
        if test_dir.exists() and not any(test_dir.iterdir()):
            test_dir.rmdir()


def test_create_snapshot_apply_profile_and_load_snapshot() -> None:
    resume_parsing = _load_resume_module()
    from app.core.security import hash_password
    from app.db import SessionLocal
    from app.models import CandidateProfile, CandidateSkill, Education, EmploymentHistory, File, ParsedProfileSnapshot, User

    reset_database_with_migrations()

    with SessionLocal() as db:
        user = User(
            email="resume-parser@example.com",
            password_hash=hash_password("password"),
            full_name=None,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

        profile = CandidateProfile(
            user_id=user.id,
            email=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
        db.flush()

        file_record = File(
            user_id=user.id,
            purpose="candidate_cv",
            blob_path=f"candidate-cv/{user.id}-resume.txt",
        )
        db.add(file_record)
        db.flush()

        parsed_payload = {
            "personal": {"full_name": "Resume Parser"},
            "contact": {
                "email": "resume-parser@example.com",
                "phone": "+61 444 222 111",
                "linkedin_url": "https://linkedin.com/in/resume-parser",
                "portfolio_url": "https://portfolio.example.com",
            },
            "skills": ["Python", "SQL", "Python"],
            "employment": [{"title": "Engineer", "company": "Talenti", "description": "Built APIs"}],
            "education": [{"institution": "UNSW", "degree": "BSc"}],
            "confidence": {"skills": 0.8},
        }
        snapshot = resume_parsing.create_parsed_snapshot(
            db,
            file_id=file_record.id,
            user_id=user.id,
            parsed=parsed_payload,
            raw_text="raw resume text",
            source_kind="candidate_cv",
        )

        resume_parsing.apply_parsed_profile(
            db,
            user=user,
            profile=profile,
            parsed=parsed_payload,
            snapshot=snapshot,
            source_kind="candidate_cv",
        )
        db.commit()

        db.refresh(profile)
        assert profile.profile_prefilled is True
        assert profile.profile_review_status == "needs_confirmation"
        assert profile.parsed_snapshot_id == snapshot.id
        assert profile.first_name == "Resume"
        assert profile.last_name == "Parser"
        assert profile.linkedin_url == "https://linkedin.com/in/resume-parser"
        assert db.query(CandidateSkill).filter(CandidateSkill.user_id == user.id).count() == 2
        assert db.query(EmploymentHistory).filter(EmploymentHistory.user_id == user.id).count() == 1
        assert db.query(Education).filter(Education.user_id == user.id).count() == 1

        loaded = resume_parsing.load_parsed_snapshot(snapshot)
        assert loaded is not None
        assert loaded["personal"]["full_name"] == "Resume Parser"

        invalid_snapshot = ParsedProfileSnapshot(
            user_id=user.id,
            file_id="file-2",
            snapshot_type="resume_parse",
            parser_version="heuristic_resume_parser_v1",
            source_kind="candidate_cv",
            data_json=json.dumps(["not-a-dict"]),
            confidence_json="{}",
            raw_text="raw",
        )
        assert resume_parsing.load_parsed_snapshot(invalid_snapshot) is None


def test_load_file_bytes_raises_when_file_missing_and_blob_disabled(monkeypatch) -> None:
    resume_parsing = _load_resume_module()
    from app.models import File

    monkeypatch.setattr(resume_parsing, "is_blob_storage_configured", lambda: False)
    file_record = File(blob_path="non-existent-path.txt", purpose="candidate_cv")
    try:
        resume_parsing.extract_resume_text(file_record)
        raise AssertionError("Expected ValueError for missing local and blob file bytes")
    except ValueError as exc:
        assert "Unable to load file bytes" in str(exc)
