"""Tests for core/config.py and db/database.py."""

from __future__ import annotations

from collections.abc import AsyncIterator

from core.config import Settings, settings
from core.i18n import BASE_LOCALE
from core.i18n import SUPPORTED_LOCALES as I18N_LOCALES
from db.database import Base, async_session_factory, get_db


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.API_V1_STR == "/api/v1"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert s.MAX_UPLOAD_SIZE > 0
        assert s.DEFAULT_LOCALE == "en"

    def test_cors_origins_parsed_from_comma_string(self) -> None:
        s = Settings(CORS_ORIGINS="http://a.example, http://b.example ,", _env_file=None)  # type: ignore[call-arg]
        assert s.CORS_ORIGINS == ["http://a.example", "http://b.example"]

    def test_cors_origins_list_passthrough(self) -> None:
        s = Settings(CORS_ORIGINS=["http://c.example"], _env_file=None)  # type: ignore[call-arg]
        assert s.CORS_ORIGINS == ["http://c.example"]

    def test_resolved_google_key_prefers_google(self) -> None:
        s = Settings(GOOGLE_API_KEY="g", GEMINI_API_KEY="m", _env_file=None)  # type: ignore[call-arg]
        assert s.resolved_google_api_key == "g"

    def test_resolved_google_key_falls_back_to_gemini(self) -> None:
        s = Settings(GOOGLE_API_KEY=None, GEMINI_API_KEY="m", _env_file=None)  # type: ignore[call-arg]
        assert s.resolved_google_api_key == "m"

    def test_resolved_google_key_none_when_missing(self) -> None:
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        s.GOOGLE_API_KEY = None
        s.GEMINI_API_KEY = None
        assert s.resolved_google_api_key is None

    def test_supported_locales_match_i18n(self) -> None:
        assert settings.SUPPORTED_LOCALES == I18N_LOCALES

    def test_supported_locales_derived_from_i18n_not_aliased(self) -> None:
        """Settings defaults derive from i18n (single source of truth) as a copy."""
        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.SUPPORTED_LOCALES is not I18N_LOCALES
        s.SUPPORTED_LOCALES.append("xx")
        assert "xx" not in I18N_LOCALES
        assert s.DEFAULT_LOCALE == BASE_LOCALE


class TestDatabase:
    async def test_get_db_yields_session_and_closes(self) -> None:
        agen: AsyncIterator = get_db()
        session = await agen.__anext__()
        assert session is not None
        await agen.aclose()

    async def test_session_factory_bound(self) -> None:
        assert async_session_factory.kw["bind"] is not None

    async def test_base_metadata_has_all_tables(self) -> None:
        expected = {"users", "resumes", "jobs", "applications"}
        assert expected == set(Base.metadata.tables.keys())
