from app.core.security import (
    PASSWORD_MIN_LENGTH,
    generate_secure_password,
    require_strong_password,
    validate_password_strength,
)


def test_validate_password_strength_rules() -> None:
    assert validate_password_strength("Abc@1234")
    assert not validate_password_strength("short1!")
    assert not validate_password_strength("noupper1!")
    assert not validate_password_strength("NOLOWER1!")
    assert not validate_password_strength("NoDigits!!")
    assert not validate_password_strength("NoSpecial1")


def test_require_strong_password_raises() -> None:
    try:
        require_strong_password("password")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "минимум 8 символов" in str(exc)


def test_generate_secure_password_matches_policy() -> None:
    for _ in range(50):
        password = generate_secure_password()
        assert len(password) == PASSWORD_MIN_LENGTH
        assert validate_password_strength(password)
