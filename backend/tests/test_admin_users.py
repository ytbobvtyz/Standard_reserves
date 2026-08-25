import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import verify_password
from app.models.user import User
from tests.conftest import (
    AuthUser,
    _create_user,
    _delete_user,
    auth_header,
    login_token,
)

NEW_USERNAME_PREFIX = "admin_created_"


def _payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "username": "new_manager",
        "email": "new_manager@company.ru",
        "full_name": "Новый Менеджер",
        "role": "commercial",
        "password": "password1",
    }
    data.update(overrides)
    return data


async def _cleanup_user(user_id: str | uuid.UUID | None) -> None:
    if not user_id:
        return
    await _delete_user(uuid.UUID(str(user_id)))


async def test_admin_users_forbidden_for_non_logistics(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    guest_user: AuthUser,
) -> None:
    for user in (test_user, pp_user, economist_user, guest_user):
        token = await login_token(client, user)
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_header(token),
        )
        assert response.status_code == 403, response.text


async def test_admin_users_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401


async def test_list_users_with_filters(
    client: AsyncClient, logistics_user: AuthUser, test_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    listed = await client.get(
        "/api/v1/admin/users",
        headers=auth_header(token),
        params={"page": 1, "limit": 50},
    )
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["status"] == "success"
    assert "meta" in body
    assert body["meta"]["page"] == 1
    usernames = {item["username"] for item in body["data"]}
    assert logistics_user.username in usernames
    assert test_user.username in usernames
    assert all("password" not in item for item in body["data"])
    assert all("password_hash" not in item for item in body["data"])

    by_role = await client.get(
        "/api/v1/admin/users",
        headers=auth_header(token),
        params={"role": "commercial"},
    )
    assert by_role.status_code == 200, by_role.text
    assert {item["role"] for item in by_role.json()["data"]} == {"commercial"}

    by_search = await client.get(
        "/api/v1/admin/users",
        headers=auth_header(token),
        params={"search": test_user.email},
    )
    assert by_search.status_code == 200, by_search.text
    found = by_search.json()["data"]
    assert any(item["username"] == test_user.username for item in found)

    by_active = await client.get(
        "/api/v1/admin/users",
        headers=auth_header(token),
        params={"is_active": True},
    )
    assert by_active.status_code == 200
    assert all(item["is_active"] is True for item in by_active.json()["data"])


async def test_create_get_update_delete_user(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    suffix = uuid.uuid4().hex[:10]
    username = f"{NEW_USERNAME_PREFIX}{suffix}"
    email = f"{NEW_USERNAME_PREFIX}{suffix}@company.ru"
    created_id: str | None = None
    try:
        created = await client.post(
            "/api/v1/admin/users",
            headers=auth_header(token),
            json=_payload(username=username, email=email),
        )
        assert created.status_code == 201, created.text
        data = created.json()["data"]
        created_id = data["id"]
        assert data["username"] == username
        assert data["email"] == email
        assert data["full_name"] == "Новый Менеджер"
        assert data["role"] == "commercial"
        assert data["is_active"] is True
        assert "password" not in data

        async with AsyncSessionLocal() as session:
            user = await session.scalar(
                select(User).where(User.id == uuid.UUID(created_id))
            )
            assert user is not None
            assert user.password_hash != "password1"
            assert verify_password("password1", user.password_hash)

        login = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "password1"},
        )
        assert login.status_code == 200, login.text

        duplicate = await client.post(
            "/api/v1/admin/users",
            headers=auth_header(token),
            json=_payload(username=username, email=f"other_{suffix}@company.ru"),
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "ALREADY_EXISTS"

        fetched = await client.get(
            f"/api/v1/admin/users/{created_id}",
            headers=auth_header(token),
        )
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["data"]["username"] == username

        updated = await client.put(
            f"/api/v1/admin/users/{created_id}",
            headers=auth_header(token),
            json={
                "email": email,
                "full_name": "Менеджер Обновлённый",
                "role": "pp",
                "department_id": None,
                "is_active": True,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["full_name"] == "Менеджер Обновлённый"
        assert updated.json()["data"]["role"] == "pp"
        assert updated.json()["data"]["username"] == username

        deleted = await client.delete(
            f"/api/v1/admin/users/{created_id}",
            headers=auth_header(token),
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["message"] == "Пользователь удален"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(
                select(User).where(User.id == uuid.UUID(created_id))
            )
            assert user is not None
            assert user.deleted_at is not None

        listed_deleted = await client.get(
            "/api/v1/admin/users",
            headers=auth_header(token),
            params={"deleted": True, "search": username},
        )
        assert listed_deleted.status_code == 200
        assert any(item["id"] == created_id for item in listed_deleted.json()["data"])

        missing = await client.get(
            "/api/v1/admin/users",
            headers=auth_header(token),
            params={"search": username},
        )
        assert all(item["id"] != created_id for item in missing.json()["data"])
    finally:
        await _cleanup_user(created_id)


async def test_cannot_delete_self(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.delete(
        f"/api/v1/admin/users/{logistics_user.id}",
        headers=auth_header(token),
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "CANNOT_DELETE_SELF"


async def test_cannot_remove_last_logistics(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    extra = await _create_user(role="logistics")
    deactivated_ids: list[uuid.UUID] = []
    try:
        deleted_extra = await client.delete(
            f"/api/v1/admin/users/{extra.id}",
            headers=auth_header(token),
        )
        assert deleted_extra.status_code == 200, deleted_extra.text

        async with AsyncSessionLocal() as session:
            others = (
                await session.scalars(
                    select(User).where(
                        User.role == "logistics",
                        User.deleted_at.is_(None),
                        User.is_active.is_(True),
                        User.id != logistics_user.id,
                    )
                )
            ).all()
            deactivated_ids = [item.id for item in others]
            for item in others:
                item.is_active = False
            await session.commit()

        role_change = await client.put(
            f"/api/v1/admin/users/{logistics_user.id}",
            headers=auth_header(token),
            json={
                "email": logistics_user.email,
                "full_name": logistics_user.full_name,
                "role": "guest",
                "department_id": None,
                "is_active": True,
            },
        )
        assert role_change.status_code == 400, role_change.text
        assert role_change.json()["error"]["code"] == "LAST_LOGISTICS"

        deactivate = await client.put(
            f"/api/v1/admin/users/{logistics_user.id}",
            headers=auth_header(token),
            json={
                "email": logistics_user.email,
                "full_name": logistics_user.full_name,
                "role": "logistics",
                "department_id": None,
                "is_active": False,
            },
        )
        assert deactivate.status_code == 400, deactivate.text
        assert deactivate.json()["error"]["code"] == "LAST_LOGISTICS"
    finally:
        async with AsyncSessionLocal() as session:
            for user_id in deactivated_ids:
                other = await session.get(User, user_id)
                if other is not None:
                    other.is_active = True
            await session.commit()
        await _delete_user(extra.id)


async def test_reset_password(client: AsyncClient, logistics_user: AuthUser) -> None:
    token = await login_token(client, logistics_user)
    target = await _create_user(role="commercial")
    try:
        response = await client.post(
            f"/api/v1/admin/users/{target.id}/reset-password",
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text
        new_password = response.json()["data"]["new_password"]
        assert isinstance(new_password, str)
        assert len(new_password) == 8

        old_login = await client.post(
            "/api/v1/auth/login",
            json={"username": target.username, "password": target.password},
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/auth/login",
            json={"username": target.username, "password": new_password},
        )
        assert new_login.status_code == 200, new_login.text
    finally:
        await _delete_user(target.id)


async def test_list_admin_departments(
    client: AsyncClient, logistics_user: AuthUser, guest_user: AuthUser
) -> None:
    guest_token = await login_token(client, guest_user)
    forbidden = await client.get(
        "/api/v1/admin/departments",
        headers=auth_header(guest_token),
    )
    assert forbidden.status_code == 403

    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/admin/departments",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, list)
    assert data
    assert {"id", "name", "is_active"} <= set(data[0].keys())
