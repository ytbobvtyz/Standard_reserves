from httpx import AsyncClient

from app.core.security import hash_password, verify_password
from tests.conftest import AuthUser

DEFAULT_PASSWORD = "password"


def test_hash_and_verify_password() -> None:
    password_hash = hash_password("password")
    assert password_hash != "password"
    assert verify_password("password", password_hash)
    assert not verify_password("wrong", password_hash)
    assert not verify_password("password", "not-a-bcrypt-hash")


async def _login(client: AsyncClient, username: str, password: str = DEFAULT_PASSWORD):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def test_login_success(client: AsyncClient, test_user: AuthUser) -> None:
    response = await _login(client, test_user.username)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] == 3600
    assert data["user"]["username"] == test_user.username
    assert data["user"]["role"] == "commercial"
    assert data["user"]["full_name"] == test_user.full_name


async def test_login_wrong_password(client: AsyncClient, test_user: AuthUser) -> None:
    response = await _login(client, test_user.username, "wrong-password")
    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_user(client: AsyncClient) -> None:
    response = await _login(client, "missing-user")
    assert response.status_code == 401


async def test_login_inactive_user(
    client: AsyncClient, inactive_user: AuthUser
) -> None:
    response = await _login(client, inactive_user.username)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


async def test_profile_without_token_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/profile")
    assert response.status_code == 401


async def test_profile_with_token_200(client: AsyncClient, test_user: AuthUser) -> None:
    login_response = await _login(client, test_user.username)
    token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["role"] == "commercial"
    assert data["last_login_at"] is not None


async def test_refresh_token(client: AsyncClient, test_user: AuthUser) -> None:
    login_response = await _login(client, test_user.username)
    refresh_token = login_response.json()["data"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["expires_in"] == 3600

    profile = await client.get(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert profile.status_code == 200


async def test_refresh_rejects_access_token(
    client: AsyncClient, test_user: AuthUser
) -> None:
    login_response = await _login(client, test_user.username)
    access_token = login_response.json()["data"]["access_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


async def test_logout(client: AsyncClient, test_user: AuthUser) -> None:
    login_response = await _login(client, test_user.username)
    tokens = login_response.json()["data"]
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Вы вышли из системы"

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


async def test_change_password(client: AsyncClient, test_user: AuthUser) -> None:
    login_response = await _login(client, test_user.username)
    access_token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": DEFAULT_PASSWORD, "new_password": "Abc@1234"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Пароль изменен"

    old_login = await _login(client, test_user.username, DEFAULT_PASSWORD)
    assert old_login.status_code == 401

    new_login = await _login(client, test_user.username, "Abc@1234")
    assert new_login.status_code == 200


async def test_change_password_wrong_old(
    client: AsyncClient, test_user: AuthUser
) -> None:
    login_response = await _login(client, test_user.username)
    access_token = login_response.json()["data"]["access_token"]
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"old_password": "not-the-password", "new_password": "Abc@1234"},
    )
    assert response.status_code == 400


async def test_change_password_rejects_weak(
    client: AsyncClient, test_user: AuthUser
) -> None:
    login_response = await _login(client, test_user.username)
    access_token = login_response.json()["data"]["access_token"]
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"old_password": DEFAULT_PASSWORD, "new_password": "new-password"},
    )
    assert response.status_code == 422


async def test_rbac_commercial_cannot_access_pp_route(
    client: AsyncClient, test_user: AuthUser
) -> None:
    login_response = await _login(client, test_user.username)
    token = login_response.json()["data"]["access_token"]
    response = await client.get(
        "/api/v1/_rbac/pp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_rbac_pp_can_access_pp_route(
    client: AsyncClient, pp_user: AuthUser
) -> None:
    login_response = await _login(client, pp_user.username)
    token = login_response.json()["data"]["access_token"]
    response = await client.get(
        "/api/v1/_rbac/pp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "pp"
