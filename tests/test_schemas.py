"""Tests for schemas.py – Pydantic models validation."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas import (
    ApplicationCreate,
    Job,
    JobCreate,
    MatchDetails,
    MatchResponse,
    MatchSections,
    Resume,
    ResumeCreate,
    Token,
    TokenPayload,
    User,
    UserCreate,
    UserInDB,
)

# ---------------------------------------------------------------------------
# TokenPayload / Token
# ---------------------------------------------------------------------------


class TestTokenSchemas:
    def test_token_payload_optional_sub(self) -> None:
        tp = TokenPayload()
        assert tp.sub is None

    def test_token_payload_with_sub(self) -> None:
        tp = TokenPayload(sub="42")
        assert tp.sub == "42"

    def test_token_creation(self) -> None:
        t = Token(access_token="abc123", token_type="bearer")
        assert t.access_token == "abc123"
        assert t.token_type == "bearer"


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class TestUserSchemas:
    def test_user_create(self) -> None:
        u = UserCreate(email="a@b.com", password="secret", full_name="Ab", is_recruiter=False)
        assert u.email == "a@b.com"
        assert u.password == "secret"

    def test_user_create_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="secret")

    def test_user_from_attributes(self) -> None:
        """User schema should work with from_attributes (ORM mode)."""
        now = datetime.now()

        class FakeORM:
            id = 1
            email = "x@y.com"
            full_name = "X Y"
            is_recruiter = False
            is_active = True
            created_at = now
            updated_at = None

        user = User.model_validate(FakeORM())
        assert user.id == 1
        assert user.email == "x@y.com"

    def test_user_in_db_has_hashed_password(self) -> None:
        now = datetime.now()
        u = UserInDB(
            id=1,
            email="u@v.com",
            full_name="U",
            is_recruiter=False,
            is_active=True,
            created_at=now,
            hashed_password="$2b$12$somehash",
        )
        assert u.hashed_password == "$2b$12$somehash"


# ---------------------------------------------------------------------------
# Resume schemas
# ---------------------------------------------------------------------------


class TestResumeSchemas:
    def test_resume_create_minimal(self) -> None:
        r = ResumeCreate(full_text="Simple resume text", file_type="text")
        assert r.full_text == "Simple resume text"

    def test_resume_from_attributes(self) -> None:
        now = datetime.now()

        class FakeORM:
            id = 1
            user_id = 1
            full_text = "Text"
            parsed_sections = {}
            skills = []
            experience = []
            education = []
            projects = []
            certifications = []
            achievements = []
            file_type = "text"
            file_path = None
            created_at = now
            updated_at = None

        resume = Resume.model_validate(FakeORM())
        assert resume.id == 1


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------


class TestJobSchemas:
    def test_job_create(self) -> None:
        j = JobCreate(
            title="Engineer",
            description_text="Build stuff",
            required_skills=[{"name": "Python", "importance": 1.0}],
        )
        assert j.title == "Engineer"
        assert len(j.required_skills) == 1

    def test_job_default_weights(self) -> None:
        j = JobCreate(title="T", description_text="D")
        assert j.priority_weights == {"skills": 0.6, "experience": 0.3, "education": 0.1}

    def test_job_from_attributes(self) -> None:
        now = datetime.now()

        class FakeORM:
            id = 5
            company_id = None
            title = "Dev"
            description_text = "Desc"
            required_skills = []
            preferred_skills = []
            responsibilities = []
            qualifications = []
            priority_weights = {"skills": 0.6, "experience": 0.3, "education": 0.1}
            created_at = now
            updated_at = None

        job = Job.model_validate(FakeORM())
        assert job.id == 5


# ---------------------------------------------------------------------------
# Application schemas
# ---------------------------------------------------------------------------


class TestApplicationSchemas:
    def test_application_create(self) -> None:
        a = ApplicationCreate(
            job_id=1,
            resume_id=2,
            full_name="Test",
            email="a@b.com",
        )
        assert a.job_id == 1
        assert a.resume_id == 2


# ---------------------------------------------------------------------------
# Match schemas
# ---------------------------------------------------------------------------


class TestMatchSchemas:
    def test_match_response(self) -> None:
        mr = MatchResponse(
            resume_id=1,
            job_id=2,
            match_score=85.5,
            match_details={"overall_match": 85.5},
            feedback={"strengths": ["Good skills"]},
        )
        assert mr.match_score == 85.5

    def test_match_details_defaults(self) -> None:
        md = MatchDetails()
        assert md.overall_match == 0.0
        assert md.sections.skills.score == 0.0
        assert md.weights_applied.skills == 0.6

    def test_match_sections_defaults(self) -> None:
        ms = MatchSections()
        assert ms.skills.required.match_rate == 0.0
        assert ms.experience.score == 0.0
        assert ms.education.highest_education is None
