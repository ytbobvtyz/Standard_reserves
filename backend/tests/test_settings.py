from pydantic import ValidationError

from app.core.config import Settings


def test_default_log_level_is_info() -> None:
    settings = Settings(
        debug=False,
        backend_cors_origins=["https://localhost"],
        database_url="postgresql://postgres:test@postgres:5432/standart_reserve",
    )
    assert settings.log_level == "INFO"
    assert settings.debug is False


def test_cors_wildcard_rejected_when_debug_false() -> None:
    try:
        Settings(
            debug=False,
            backend_cors_origins=["*"],
            database_url="postgresql://postgres:test@postgres:5432/standart_reserve",
        )
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        assert "BACKEND_CORS_ORIGINS" in str(exc)


def test_database_url_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:from-env@postgres:5432/standart_reserve",
    )
    settings = Settings(_env_file=None)
    assert (
        settings.database_url
        == "postgresql://postgres:from-env@postgres:5432/standart_reserve"
    )
    assert settings.async_database_url.startswith(
        "postgresql+asyncpg://postgres:from-env@"
    )


def test_database_url_required(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    try:
        Settings(_env_file=None)
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        assert "database_url" in str(exc)
