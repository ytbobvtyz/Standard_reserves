import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.event import Event
from tests.conftest import (
    AuthUser,
    _create_user,
    _delete_user,
    auth_header,
    login_token,
)


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


async def test_admin_inherits_logistics_users(
    client: AsyncClient, admin_user: AuthUser
) -> None:
    token = await login_token(client, admin_user)
    response = await client.get(
        "/api/v1/admin/users",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    usernames = {item["username"] for item in response.json()["data"]}
    assert admin_user.username in usernames


async def test_audit_forbidden_for_logistics(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/admin/audit",
        headers=auth_header(token),
        params={"date_from": _today(), "date_to": _today()},
    )
    assert response.status_code == 403, response.text


async def test_audit_requires_dates(client: AsyncClient, admin_user: AuthUser) -> None:
    token = await login_token(client, admin_user)
    response = await client.get(
        "/api/v1/admin/audit",
        headers=auth_header(token),
    )
    assert response.status_code == 422, response.text


async def test_user_registration_is_listed(
    client: AsyncClient, admin_user: AuthUser
) -> None:
    token = await login_token(client, admin_user)
    username = f"audit_{uuid.uuid4().hex[:8]}"
    created_id: str | None = None
    try:
        created = await client.post(
            "/api/v1/admin/users",
            headers=auth_header(token),
            json={
                "username": username,
                "email": f"{username}@company.ru",
                "full_name": "Журнал Тест",
                "role": "guest",
                "password": "Abc@1234",
            },
        )
        assert created.status_code == 201, created.text
        created_id = created.json()["data"]["id"]

        listed = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(token),
            params={
                "date_from": _today(),
                "date_to": _today(),
                "event_type": "user_registered",
                "user_id": str(admin_user.id),
                "entity_type": "user",
            },
        )
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["status"] == "success"
        rows = [
            item
            for item in body["data"]
            if item.get("entity_id") == created_id
            or (item.get("details") or {}).get("username") == username
        ]
        assert rows, body
        match = rows[0]
        assert match["event_type"] == "user_registered"
        assert match["entity_label"] == f"Журнал Тест ({username})"
        assert match["user"]["id"] == str(admin_user.id)
        assert match["user"]["role"] == "admin"
        assert match["details"]["username"] == username
        assert "password" not in match["details"]
        assert body["meta"]["total"] >= 1
    finally:
        if created_id:
            await _delete_user(uuid.UUID(created_id))


async def test_audit_date_filter_excludes_old_events(
    client: AsyncClient, admin_user: AuthUser
) -> None:
    token = await login_token(client, admin_user)
    event_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Event(
                id=event_id,
                event_type="export_generated",
                user_id=admin_user.id,
                entity_type="upload",
                payload={"label": "Старый экспорт"},
                details={"label": "Старый экспорт"},
                processed=False,
                created_at=datetime.now(UTC) - timedelta(days=40),
            )
        )
        await session.commit()
    try:
        yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
        old_day = (datetime.now(UTC) - timedelta(days=40)).date().isoformat()
        missed = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(token),
            params={
                "date_from": _today(),
                "date_to": _today(),
                "event_type": "export_generated",
            },
        )
        assert missed.status_code == 200, missed.text
        assert all(item["id"] != str(event_id) for item in missed.json()["data"])

        found = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(token),
            params={
                "date_from": old_day,
                "date_to": yesterday,
                "event_type": "export_generated",
            },
        )
        assert found.status_code == 200, found.text
        row = next(item for item in found.json()["data"] if item["id"] == str(event_id))
        assert row["entity_label"] == "Старый экспорт"
        assert row["user"]["full_name"] == admin_user.full_name
    finally:
        async with AsyncSessionLocal() as session:
            event = await session.scalar(select(Event).where(Event.id == event_id))
            if event is not None:
                await session.delete(event)
                await session.commit()


async def test_audit_filters_by_request_number(
    client: AsyncClient, admin_user: AuthUser
) -> None:
    token = await login_token(client, admin_user)
    request_id = uuid.uuid4()
    other_id = uuid.uuid4()
    match_id = uuid.uuid4()
    miss_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                Event(
                    id=match_id,
                    event_type="request_created",
                    entity_type="request",
                    entity_id=request_id,
                    payload={"label": "Нужный запрос"},
                    details={"label": "Нужный запрос"},
                    processed=False,
                ),
                Event(
                    id=miss_id,
                    event_type="request_created",
                    entity_type="request",
                    entity_id=other_id,
                    payload={"label": "Другой запрос"},
                    details={"label": "Другой запрос"},
                    processed=False,
                ),
            ]
        )
        await session.commit()
    try:
        found = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(token),
            params={
                "date_from": _today(),
                "date_to": _today(),
                "request_number": f"№{str(request_id)[:8]}",
            },
        )
        assert found.status_code == 200, found.text
        ids = {item["id"] for item in found.json()["data"]}
        assert str(match_id) in ids
        assert str(miss_id) not in ids

        unknown = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(token),
            params={
                "date_from": _today(),
                "date_to": _today(),
                "request_number": "не номер",
            },
        )
        assert unknown.status_code == 200, unknown.text
        assert unknown.json()["data"] == []
    finally:
        async with AsyncSessionLocal() as session:
            rows = await session.scalars(
                select(Event).where(Event.id.in_([match_id, miss_id]))
            )
            for event in rows:
                await session.delete(event)
            await session.commit()


async def test_password_change_is_logged(
    client: AsyncClient, admin_user: AuthUser
) -> None:
    target = await _create_user(role="commercial")
    try:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": target.username, "password": target.password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["data"]["access_token"]
        changed = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_header(token),
            json={"old_password": target.password, "new_password": "Abc@1234"},
        )
        assert changed.status_code == 200, changed.text

        admin_token = await login_token(client, admin_user)
        listed = await client.get(
            "/api/v1/admin/audit",
            headers=auth_header(admin_token),
            params={
                "date_from": _today(),
                "date_to": _today(),
                "event_type": "password_changed",
                "user_id": str(target.id),
            },
        )
        assert listed.status_code == 200, listed.text
        row = listed.json()["data"][0]
        assert row["entity_id"] == str(target.id)
        assert row["details"]["source"] == "self"
        assert "password" not in row["details"]
    finally:
        await _delete_user(target.id)
