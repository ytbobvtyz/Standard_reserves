from pydantic import ValidationError

from app.core.config import Settings


def test_default_log_level_is_info() -> None:
    settings = Settings(
        debug=False,
        backend_cors_origins=["https://localhost"],
    )
    assert settings.log_level == "INFO"
    assert settings.debug is False


def test_cors_wildcard_rejected_when_debug_false() -> None:
    try:
        Settings(debug=False, backend_cors_origins=["*"])
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        assert "BACKEND_CORS_ORIGINS" in str(exc)
