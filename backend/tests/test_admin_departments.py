import uuid

from httpx import AsyncClient
from sqlalchemy import delete, select, update

from app.core.database import AsyncSessionLocal
from app.models.department import Department
from app.models.request import Request
from app.models.user import User
from tests.conftest import (
    AuthUser,
    _create_user,
    _delete_user,
    auth_header,
    login_token,
)


async def _cleanup_department(department_id: str | uuid.UUID | None) -> None:
    if not department_id:
        return
    dept_id = uuid.UUID(str(department_id))
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.department_id == dept_id)
            .values(department_id=None, department=None)
        )
        await session.execute(
            update(Request)
            .where(Request.department_id == dept_id)
            .values(department_id=None)
        )
        await session.execute(delete(Department).where(Department.id == dept_id))
        await session.commit()


async def test_create_department(client: AsyncClient, logistics_user: AuthUser) -> None:
    token = await login_token(client, logistics_user)
    name = f"Отдел {uuid.uuid4().hex[:8]}"
    created_id = None
    try:
        response = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": f"  {name}  "},
        )
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        created_id = data["id"]
        assert data["name"] == name
        assert data["is_active"] is True
        assert data["users_count"] == 0
    finally:
        await _cleanup_department(created_id)


async def test_create_department_duplicate(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    name = f"Дубль {uuid.uuid4().hex[:8]}"
    created_id = None
    try:
        first = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": name},
        )
        assert first.status_code == 201, first.text
        created_id = first.json()["data"]["id"]

        duplicate = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": name},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "ALREADY_EXISTS"
    finally:
        await _cleanup_department(created_id)


async def test_rename_department_syncs_user_text(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    name = f"Старое {uuid.uuid4().hex[:8]}"
    renamed = f"Новое {uuid.uuid4().hex[:8]}"
    created_id = None
    extra = await _create_user(role="commercial")
    try:
        created = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": name},
        )
        assert created.status_code == 201, created.text
        created_id = created.json()["data"]["id"]

        assigned = await client.put(
            f"/api/v1/admin/users/{extra.id}",
            headers=auth_header(token),
            json={
                "email": extra.email,
                "full_name": extra.full_name,
                "role": extra.role,
                "department_id": created_id,
                "is_active": True,
            },
        )
        assert assigned.status_code == 200, assigned.text

        response = await client.put(
            f"/api/v1/admin/departments/{created_id}",
            headers=auth_header(token),
            json={"name": renamed},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["name"] == renamed
        assert response.json()["data"]["users_count"] == 1

        user = await client.get(
            f"/api/v1/admin/users/{extra.id}",
            headers=auth_header(token),
        )
        assert user.status_code == 200, user.text
        assert user.json()["data"]["department_name"] == renamed

        async with AsyncSessionLocal() as session:
            stored = await session.scalar(
                select(User.department).where(User.id == extra.id)
            )
        assert stored == renamed
    finally:
        await _delete_user(extra.id)
        await _cleanup_department(created_id)


async def test_delete_empty_department(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    created_id = None
    try:
        created = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": f"Пустое {uuid.uuid4().hex[:8]}"},
        )
        assert created.status_code == 201, created.text
        created_id = created.json()["data"]["id"]

        deleted = await client.delete(
            f"/api/v1/admin/departments/{created_id}",
            headers=auth_header(token),
        )
        assert deleted.status_code == 200, deleted.text

        listed = await client.get(
            "/api/v1/admin/departments",
            headers=auth_header(token),
        )
        assert listed.status_code == 200
        ids = {item["id"] for item in listed.json()["data"]}
        assert created_id not in ids
    finally:
        await _cleanup_department(created_id)


async def test_delete_department_with_users(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    created_id = None
    extra = await _create_user(role="commercial")
    try:
        created = await client.post(
            "/api/v1/admin/departments",
            headers=auth_header(token),
            json={"name": f"Занятое {uuid.uuid4().hex[:8]}"},
        )
        assert created.status_code == 201, created.text
        created_id = created.json()["data"]["id"]

        assigned = await client.put(
            f"/api/v1/admin/users/{extra.id}",
            headers=auth_header(token),
            json={
                "email": extra.email,
                "full_name": extra.full_name,
                "role": extra.role,
                "department_id": created_id,
                "is_active": True,
            },
        )
        assert assigned.status_code == 200, assigned.text

        blocked = await client.delete(
            f"/api/v1/admin/departments/{created_id}",
            headers=auth_header(token),
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "HAS_RELATIONS"
    finally:
        await _delete_user(extra.id)
        await _cleanup_department(created_id)


async def test_admin_departments_forbidden_for_non_logistics(
    client: AsyncClient, guest_user: AuthUser
) -> None:
    token = await login_token(client, guest_user)
    headers = auth_header(token)
    listed = await client.get("/api/v1/admin/departments", headers=headers)
    assert listed.status_code == 403

    created = await client.post(
        "/api/v1/admin/departments",
        headers=headers,
        json={"name": "Запрещено"},
    )
    assert created.status_code == 403

    fake_id = uuid.uuid4()
    updated = await client.put(
        f"/api/v1/admin/departments/{fake_id}",
        headers=headers,
        json={"name": "Запрещено"},
    )
    assert updated.status_code == 403

    deleted = await client.delete(
        f"/api/v1/admin/departments/{fake_id}",
        headers=headers,
    )
    assert deleted.status_code == 403
