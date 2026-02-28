import pytest

from services import AIService


@pytest.mark.asyncio
async def test_parse_resume_fallback_without_provider() -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]

    parsed = await service.parse_resume(
        "Jane Doe\nBackend Engineer\nEmail: jane@example.com\nPhone: +91 9999999999\nPython FastAPI SQL"
    )

    assert "parsed_sections" in parsed
    assert "skills" in parsed
    assert parsed["parsed_sections"]["contact"]["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_calculate_match_score_fallback() -> None:
    service = AIService()

    async def _no_call(*args, **kwargs):
        return None

    service._call_text = _no_call  # type: ignore[method-assign]

    score, details = await service.calculate_match_score(
        {"skills": [{"name": "Python"}, {"name": "SQL"}], "experience": [{}], "education": [{}]},
        {
            "required_skills": [{"name": "Python"}, {"name": "FastAPI"}],
            "preferred_skills": [{"name": "Docker"}],
        },
    )

    assert score >= 0
    assert "sections" in details
    assert "skills" in details["sections"]
