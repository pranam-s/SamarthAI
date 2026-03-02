"""Tests for core/i18n.py – translation system."""

from __future__ import annotations

from core.i18n import (
    BASE_LOCALE,
    EN_TRANSLATIONS,
    LOCALE_OVERRIDES,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    normalize_locale,
    translate,
)

# ---------------------------------------------------------------------------
# normalize_locale
# ---------------------------------------------------------------------------


class TestNormalizeLocale:
    def test_extracts_base_from_regional_tag(self) -> None:
        assert normalize_locale("hi-IN") == "hi"

    def test_returns_supported_locale(self) -> None:
        assert normalize_locale("fr") == "fr"
        assert normalize_locale("de") == "de"
        assert normalize_locale("ja") == "ja"

    def test_returns_base_for_unsupported(self) -> None:
        assert normalize_locale("unknown") == BASE_LOCALE
        assert normalize_locale("zz") == BASE_LOCALE

    def test_returns_base_for_none(self) -> None:
        assert normalize_locale(None) == BASE_LOCALE

    def test_returns_base_for_empty(self) -> None:
        assert normalize_locale("") == BASE_LOCALE

    def test_handles_accept_language_format(self) -> None:
        assert normalize_locale("es,en;q=0.9") == "es"
        assert normalize_locale("fr-FR,fr;q=0.9") == "fr"

    def test_case_insensitive(self) -> None:
        assert normalize_locale("HI") == "hi"
        assert normalize_locale("EN") == "en"


# ---------------------------------------------------------------------------
# translate
# ---------------------------------------------------------------------------


class TestTranslate:
    def test_returns_english_for_english_locale(self) -> None:
        assert translate("en", "nav.home") == "Home"

    def test_returns_translated_for_supported_locale(self) -> None:
        result = translate("hi", "nav.home")
        assert result == "होम"

    def test_falls_back_to_english_for_unknown_locale(self) -> None:
        assert translate("unknown", "nav.home") == "Home"

    def test_falls_back_to_english_for_missing_key(self) -> None:
        result = translate("hi", "home.feature.ai_resume_analysis")
        assert result == "AI Resume Analysis"  # Not in hi overrides -> EN

    def test_returns_key_for_completely_missing_key(self) -> None:
        result = translate("en", "this.key.does.not.exist")
        assert result == "this.key.does.not.exist"

    def test_all_en_keys_present(self) -> None:
        en_keys = set(TRANSLATIONS["en"].keys())
        assert en_keys == set(EN_TRANSLATIONS.keys())


# ---------------------------------------------------------------------------
# TRANSLATIONS structure
# ---------------------------------------------------------------------------


class TestTranslationsStructure:
    def test_all_supported_locales_present(self) -> None:
        for locale in SUPPORTED_LOCALES:
            assert locale in TRANSLATIONS, f"Locale {locale} not in TRANSLATIONS"

    def test_all_locales_have_all_en_keys(self) -> None:
        """All locales should have all EN keys (either translated or inherited)."""
        en_keys = set(EN_TRANSLATIONS.keys())
        for locale in SUPPORTED_LOCALES:
            locale_keys = set(TRANSLATIONS[locale].keys())
            assert locale_keys == en_keys, (
                f"Locale {locale!r} key set mismatch. "
                f"Missing: {en_keys - locale_keys}, Extra: {locale_keys - en_keys}"
            )

    def test_override_keys_are_valid(self) -> None:
        """All override keys must exist in EN_TRANSLATIONS."""
        for locale, overrides in LOCALE_OVERRIDES.items():
            for key in overrides:
                assert key in EN_TRANSLATIONS, (
                    f"Override key {key!r} in locale {locale!r} not in EN_TRANSLATIONS"
                )

    def test_twenty_locales_supported(self) -> None:
        assert len(SUPPORTED_LOCALES) >= 20

    def test_en_translations_nonempty(self) -> None:
        assert len(EN_TRANSLATIONS) > 100
