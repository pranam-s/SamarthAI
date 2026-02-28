from core.i18n import normalize_locale, translate


def test_normalize_locale_prefers_supported_language() -> None:
    assert normalize_locale("hi-IN") == "hi"
    assert normalize_locale("fr") == "fr"


def test_translate_falls_back_to_english() -> None:
    assert translate("de", "nav.home") != "nav.home"
    assert translate("unknown", "nav.home") == "Home"
