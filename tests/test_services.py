"""Tests for services.py – AIService, ResumeService, JobService, MatchingService, UserService."""

from __future__ import annotations

import pytest

from services import AIService

# ---------------------------------------------------------------------------
# AIService.parse_json
# ---------------------------------------------------------------------------


class TestParseJson:
    """AIService.parse_json should extract the first valid JSON object from text."""

    def test_extracts_embedded_object(self) -> None:
        parsed = AIService.parse_json('prefix text {"a": 1, "b": {"c": true}} suffix')
        assert parsed["a"] == 1
        assert parsed["b"]["c"] is True

    def test_handles_nested_braces(self) -> None:
        payload = '{"outer": {"inner": {"deep": 42}}}'
        assert AIService.parse_json(payload)["outer"]["inner"]["deep"] == 42

    def test_rejects_invalid_payload(self) -> None:
        with pytest.raises(ValueError, match="No JSON object"):
            AIService.parse_json("no valid object here")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError):
            AIService.parse_json("")

    def test_extracts_first_object_only(self) -> None:
        text = '{"a": 1} {"b": 2}'
        parsed = AIService.parse_json(text)
        assert parsed == {"a": 1}

    def test_handles_json_with_arrays(self) -> None:
        text = '{"skills": ["python", "java"], "count": 2}'
        parsed = AIService.parse_json(text)
        assert parsed["skills"] == ["python", "java"]
        assert parsed["count"] == 2

    def test_handles_escaped_braces_in_strings(self) -> None:
        text = '{"msg": "use \\\\{ for literal braces", "ok": true}'
        parsed = AIService.parse_json(text)
        assert parsed["ok"] is True


# ---------------------------------------------------------------------------
# AIService._extract_skill_names
# ---------------------------------------------------------------------------


class TestExtractSkillNames:
    """Test the static skill-name extraction helper."""

    def test_extracts_from_dict_list(self) -> None:
        skills = [{"name": "Python"}, {"name": "SQL"}, {"name": "Docker"}]
        result = AIService._extract_skill_names(skills)
        assert result == ["python", "sql", "docker"]

    def test_extracts_from_string_list(self) -> None:
        skills = ["React", "TypeScript"]
        result = AIService._extract_skill_names(skills)
        assert result == ["react", "typescript"]

    def test_returns_empty_for_non_list(self) -> None:
        assert AIService._extract_skill_names(None) == []
        assert AIService._extract_skill_names("python") == []
        assert AIService._extract_skill_names(42) == []

    def test_skips_items_without_name(self) -> None:
        skills = [{"name": "Go"}, {"proficiency": "expert"}, {"name": "Rust"}]
        result = AIService._extract_skill_names(skills)
        assert result == ["go", "rust"]

    def test_strips_whitespace(self) -> None:
        skills = [{"name": "  Python  "}, " SQL "]
        result = AIService._extract_skill_names(skills)
        assert result == ["python", "sql"]


# ---------------------------------------------------------------------------
# AIService._default_resume_payload
# ---------------------------------------------------------------------------


class TestDefaultResumePayload:
    """Test the heuristic resume parser (fallback when AI is unavailable)."""

    def test_extracts_email(self) -> None:
        payload = AIService._default_resume_payload("Jane\njane@example.com")
        assert payload["parsed_sections"]["contact"]["email"] == "jane@example.com"

    def test_extracts_phone(self) -> None:
        payload = AIService._default_resume_payload("Jane\n+91 9999999999")
        assert "9999999999" in payload["parsed_sections"]["contact"]["phone"]

    def test_extracts_name_from_first_line(self) -> None:
        payload = AIService._default_resume_payload("John Smith\nDeveloper")
        assert payload["parsed_sections"]["contact"]["name"] == "John Smith"

    def test_detects_skill_keywords(self) -> None:
        text = "I know Python and Docker and FastAPI"
        payload = AIService._default_resume_payload(text)
        skill_names = [s["name"].lower() for s in payload["skills"]]
        assert "python" in skill_names
        assert "docker" in skill_names
        assert "fastapi" in skill_names

    def test_returns_all_required_keys(self) -> None:
        payload = AIService._default_resume_payload("Simple text")
        for key in (
            "parsed_sections",
            "skills",
            "experience",
            "education",
            "projects",
            "certifications",
            "achievements",
        ):
            assert key in payload

    def test_handles_empty_text(self) -> None:
        payload = AIService._default_resume_payload("")
        assert payload["parsed_sections"]["contact"]["name"] == ""
        assert payload["parsed_sections"]["contact"]["email"] == ""


# ---------------------------------------------------------------------------
# AIService._default_job_payload
# ---------------------------------------------------------------------------


class TestDefaultJobPayload:
    """Test heuristic job description parser."""

    def test_extracts_title_from_first_line(self) -> None:
        payload = AIService._default_job_payload("Senior Backend Engineer\nWe are hiring")
        assert payload["title"] == "Senior Backend Engineer"

    def test_detects_required_skills(self) -> None:
        text = "Python engineer needed with Docker and SQL experience"
        payload = AIService._default_job_payload(text)
        names = [s["name"].lower() for s in payload["required_skills"]]
        assert "python" in names
        assert "docker" in names
        assert "sql" in names

    def test_handles_empty_text(self) -> None:
        payload = AIService._default_job_payload("")
        assert payload["title"] == "Untitled Job"

    def test_returns_all_required_keys(self) -> None:
        payload = AIService._default_job_payload("Job Description")
        for key in (
            "title",
            "required_skills",
            "preferred_skills",
            "responsibilities",
            "qualifications",
        ):
            assert key in payload


# ---------------------------------------------------------------------------
# AIService._get_mime_type
# ---------------------------------------------------------------------------


class TestGetMimeType:
    """Test MIME type detection by file extension."""

    def test_pdf(self) -> None:
        assert AIService._get_mime_type("file.pdf") == "application/pdf"

    def test_txt(self) -> None:
        assert AIService._get_mime_type("file.txt") == "text/plain"

    def test_jpg(self) -> None:
        assert AIService._get_mime_type("photo.jpg") == "image/jpeg"

    def test_unknown_extension(self) -> None:
        assert AIService._get_mime_type("data.xyz") == "application/octet-stream"

    def test_case_insensitive(self) -> None:
        assert AIService._get_mime_type("file.PDF") == "application/pdf"


# ---------------------------------------------------------------------------
# AIService._heuristic_match_score
# ---------------------------------------------------------------------------


class TestHeuristicMatchScore:
    """Test the deterministic match scoring fallback."""

    def test_perfect_skills_match(self) -> None:
        service = AIService()
        resume = {
            "skills": [{"name": "Python"}, {"name": "SQL"}],
            "experience": [{}],
            "education": [{}],
        }
        job = {"required_skills": [{"name": "Python"}, {"name": "SQL"}], "preferred_skills": []}

        score, details = service._heuristic_match_score(resume, job)
        assert score > 0
        assert details["sections"]["skills"]["required"]["match_rate"] == 100.0

    def test_no_match(self) -> None:
        service = AIService()
        resume = {"skills": [{"name": "Go"}], "experience": [], "education": []}
        job = {"required_skills": [{"name": "Python"}, {"name": "SQL"}], "preferred_skills": []}

        score, details = service._heuristic_match_score(resume, job)
        assert details["sections"]["skills"]["required"]["match_rate"] == 0.0

    def test_partial_match(self) -> None:
        service = AIService()
        resume = {"skills": [{"name": "Python"}], "experience": [{}], "education": [{}]}
        job = {"required_skills": [{"name": "Python"}, {"name": "SQL"}], "preferred_skills": []}

        score, details = service._heuristic_match_score(resume, job)
        assert details["sections"]["skills"]["required"]["match_rate"] == 50.0

    def test_experience_present_increases_score(self) -> None:
        service = AIService()
        base = {"skills": [], "education": []}
        job = {"required_skills": [], "preferred_skills": []}

        _, d1 = service._heuristic_match_score({**base, "experience": []}, job)
        _, d2 = service._heuristic_match_score({**base, "experience": [{}]}, job)
        assert d2["sections"]["experience"]["score"] > d1["sections"]["experience"]["score"]

    def test_education_present_increases_score(self) -> None:
        service = AIService()
        base = {"skills": [], "experience": []}
        job = {"required_skills": [], "preferred_skills": []}

        _, d1 = service._heuristic_match_score({**base, "education": []}, job)
        _, d2 = service._heuristic_match_score({**base, "education": [{}]}, job)
        assert d2["sections"]["education"]["score"] > d1["sections"]["education"]["score"]

    def test_weights_applied(self) -> None:
        service = AIService()
        resume = {"skills": [], "experience": [], "education": []}
        job = {"required_skills": [], "preferred_skills": []}

        _, details = service._heuristic_match_score(resume, job)
        assert details["weights_applied"] == {"skills": 0.6, "experience": 0.3, "education": 0.1}


# ---------------------------------------------------------------------------
# AIService parse_resume / calculate_match_score (async, AI disabled)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_resume_fallback_without_provider(sample_resume_text: str) -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]
    parsed = await service.parse_resume(sample_resume_text)

    assert "parsed_sections" in parsed
    assert "skills" in parsed
    assert parsed["parsed_sections"]["contact"]["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_parse_job_fallback_without_provider() -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]
    parsed = await service.parse_job_description("Backend Engineer\nRequires Python and SQL")

    assert parsed["title"] == "Backend Engineer"
    names = [s["name"].lower() for s in parsed["required_skills"]]
    assert "python" in names
    assert "sql" in names


@pytest.mark.asyncio
async def test_calculate_match_score_fallback(
    sample_parsed_resume: dict, sample_parsed_job: dict
) -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]
    score, details = await service.calculate_match_score(sample_parsed_resume, sample_parsed_job)

    assert 0 <= score <= 100
    assert "sections" in details
    assert "skills" in details["sections"]


@pytest.mark.asyncio
async def test_generate_resume_feedback_fallback(
    sample_parsed_resume: dict, sample_parsed_job: dict
) -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]

    _, match_details = service._heuristic_match_score(sample_parsed_resume, sample_parsed_job)
    feedback = await service.generate_resume_feedback(
        sample_parsed_resume, sample_parsed_job, match_details
    )

    assert "strengths" in feedback
    assert "improvements" in feedback
    assert "missing_skills" in feedback
    assert "keyword_recommendations" in feedback
    assert isinstance(feedback["strengths"], list)
