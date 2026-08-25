from datetime import UTC, date, datetime
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.normative import Normative
from app.models.request import Request
from tests.conftest import AuthUser, auth_header, delete_request, login_token


def valid_expiry_date(months: int = 3) -> str:
    return Request.add_months(date.today(), months).isoformat()


def too_far_expiry_date() -> str:
    return Request.add_months(date.today(), 7).isoformat()


def too_soon_expiry_date() -> str:
    return Request.add_months(date.today(), 2).isoformat()


def request_payload(**overrides):
    payload = {
        "request_type": "normative",
        "client_name": "ООО Ромашка",
        "expiry_date": valid_expiry_date(),
        "items": [
            {
                "product_code": 10001,
                "warehouse_code": 2001,
                "quantity_requested": 1000,
                "unit": "шт",
            }
        ],
        "comment": "Тестовый запрос",
    }
    payload.update(overrides)
    return payload


async def _create(client: AsyncClient, token: str, **overrides) -> tuple[int, dict]:
    response = await client.post(
        "/api/v1/requests",
        headers=auth_header(token),
        json=request_payload(**overrides),
    )
    return response.status_code, response.json()


async def test_create_request_normative_success(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 1000,
                "unit": "шт",
            },
            {
                "product_code": catalog["product_code_2"],
                "warehouse_code": catalog["warehouse_code_2"],
                "quantity_requested": 500,
                "unit": "шт",
            },
        ],
    )
    assert status == 201, body
    data = body["data"]
    assert data["status"] == "draft"
    assert data["request_type"] == "normative"
    assert data["client_name"] == "ООО Ромашка"
    assert data["initiator_id"] == str(test_user.id)
    assert data["department_id"] is not None
    assert len(data["items"]) == 2
    first = next(
        item
        for item in data["items"]
        if item["product_code"] == catalog["product_code"]
    )
    assert first["requirement"] == 1000
    assert first["category_factor"] == 1
    assert first["long_distance"] is False
    await delete_request(data["id"])


async def test_create_request_one_time_success(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        request_type="one_time",
        expiry_date=None,
        comment="Разовое перемещение",
    )
    assert status == 201, body
    assert body["data"]["request_type"] == "one_time"
    assert body["data"]["status"] == "draft"
    await delete_request(body["data"]["id"])


async def test_create_request_without_expiry_date_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    status, body = await _create(client, token, expiry_date=None)
    assert status == 400
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_logistics_cannot_create_normative(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, logistics_user)
    status, body = await _create(client, token)
    assert status == 403
    assert body["error"]["code"] == "FORBIDDEN"


async def test_update_draft_success(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={"client_name": "ООО Тюльпан", "comment": "Уточненный объем"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "draft"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert detail.json()["data"]["client_name"] == "ООО Тюльпан"
    assert detail.json()["data"]["initiator_comment"] == "Уточненный объем"
    await delete_request(request_id)


async def test_update_not_draft_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    submit = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(token),
    )
    assert submit.status_code == 200

    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={"client_name": "ООО Тюльпан"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATUS"
    await delete_request(request_id)


async def test_delete_draft_success(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.delete(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Запрос удален"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert detail.status_code == 404
    await delete_request(request_id)


async def test_submit_draft_to_pp(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "pp_approved"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert detail.json()["data"]["status"] == "pp_approved"
    await delete_request(request_id)


async def test_commercial_sees_only_own_requests(
    client: AsyncClient,
    test_user: AuthUser,
    other_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    own_token = await login_token(client, test_user)
    other_token = await login_token(client, other_user)
    _, own = await _create(client, own_token, client_name="Свой клиент")
    _, foreign = await _create(client, other_token, client_name="Чужой клиент")

    response = await client.get("/api/v1/requests", headers=auth_header(own_token))
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert own["data"]["id"] in ids
    assert foreign["data"]["id"] not in ids

    await delete_request(own["data"]["id"])
    await delete_request(foreign["data"]["id"])


async def test_pp_sees_all_requests(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    _, created = await _create(client, commercial_token, client_name="Виден ПП")
    pp_token = await login_token(client, pp_user)
    response = await client.get("/api/v1/requests", headers=auth_header(pp_token))
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert created["data"]["id"] in ids
    await delete_request(created["data"]["id"])


async def test_request_item_history(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    status, body = await _create(client, commercial_token)
    assert status == 201, body
    request_id = body["data"]["id"]
    submit = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(commercial_token),
    )
    assert submit.status_code == 200, submit.text
    edit = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "approve",
            "items": [
                {
                    "product_code": catalog["product_code"],
                    "warehouse_code": catalog["warehouse_code"],
                    "quantity_approved": 800,
                }
            ],
            "comment": "Снижаем объем на 20%",
        },
    )
    assert edit.status_code == 200, edit.text

    response = await client.get(
        f"/api/v1/requests/{request_id}/history",
        headers=auth_header(commercial_token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data
    entry = data[0]
    assert entry["field_name"] == "quantity_approved"
    assert entry["old_value"] is None
    assert entry["new_value"] == 800
    assert entry["changed_by"]["id"] == str(pp_user.id)
    assert entry["changed_by"]["full_name"] == pp_user.full_name
    assert entry["comment"] == "Снижаем объем на 20%"
    assert "item_id" in entry
    assert "changed_at" in entry
    await delete_request(request_id)


async def _set_status(request_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        request = await session.get(Request, UUID(request_id))
        assert request is not None
        request.status = status
        await session.commit()


async def test_delete_allowed_statuses(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    for status in ("pp_approved", "economy_check", "rejected", "expired"):
        _, created = await _create(client, token, client_name=f"Удаление {status}")
        request_id = created["data"]["id"]
        await _set_status(request_id, status)
        response = await client.delete(
            f"/api/v1/requests/{request_id}",
            headers=auth_header(token),
        )
        assert response.status_code == 200, (status, response.text)
        assert response.json()["message"] == "Запрос удален"
        detail = await client.get(
            f"/api/v1/requests/{request_id}",
            headers=auth_header(token),
        )
        assert detail.status_code == 404
        await delete_request(request_id)


async def test_delete_forbidden_for_final_statuses(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    for status in ("active", "approved", "executed"):
        _, created = await _create(client, token, client_name=f"Запрет {status}")
        request_id = created["data"]["id"]
        await _set_status(request_id, status)
        response = await client.delete(
            f"/api/v1/requests/{request_id}",
            headers=auth_header(token),
        )
        assert response.status_code == 400, (status, response.text)
        assert response.json()["error"]["code"] == "BAD_REQUEST"
        assert (
            response.json()["error"]["message"]
            == "Невозможно удалить запрос после финального согласования"
        )
        await delete_request(request_id)


async def test_delete_not_owner_forbidden(
    client: AsyncClient,
    test_user: AuthUser,
    other_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    owner_token = await login_token(client, test_user)
    other_token = await login_token(client, other_user)
    _, created = await _create(client, owner_token)
    request_id = created["data"]["id"]
    response = await client.delete(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(other_token),
    )
    assert response.status_code == 403
    assert response.json()["error"]["message"] == (
        "Только инициатор может удалить запрос"
    )
    await delete_request(request_id)


async def test_delete_expired_marks_normatives(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    async with AsyncSessionLocal() as session:
        session.add(
            Normative(
                request_id=UUID(request_id),
                product_code=catalog["product_code"],
                warehouse_code=catalog["warehouse_code"],
                quantity=1000,
                unit="шт",
                client_name="ООО Ромашка",
                expiry_date=date.today(),
                category="A",
            )
        )
        await session.commit()
    await _set_status(request_id, "expired")
    response = await client.delete(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as session:
        normative = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).one()
        assert normative.deleted_at is not None
    await delete_request(request_id)


async def test_update_draft_expiry_can_increase(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token, expiry_date=valid_expiry_date(3))
    request_id = created["data"]["id"]
    new_expiry = valid_expiry_date(5)
    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={"expiry_date": new_expiry},
    )
    assert response.status_code == 200, response.text
    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    assert detail.json()["data"]["expiry_date"] == new_expiry
    await delete_request(request_id)


def test_validate_expiry_date_method() -> None:
    created_at = datetime(2026, 8, 21, tzinfo=UTC)
    max_date = Request.add_months(date(2026, 8, 21), 6)
    min_date = Request.add_months(date(2026, 8, 21), 3)
    assert Request.validate_expiry_date(max_date, created_at)
    assert Request.validate_expiry_date(min_date, created_at)
    assert Request.validate_expiry_date(date(2026, 11, 21), created_at)
    assert not Request.validate_expiry_date(date(2026, 10, 21), created_at)
    assert not Request.validate_expiry_date(Request.add_months(max_date, 1), created_at)


async def test_create_request_expiry_too_far_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    status, body = await _create(client, token, expiry_date=too_far_expiry_date())
    assert status == 400, body
    assert body["error"]["code"] == "INVALID_EXPIRY_DATE"


async def test_create_request_expiry_too_soon_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    status, body = await _create(client, token, expiry_date=too_soon_expiry_date())
    assert status == 400, body
    assert body["error"]["code"] == "INVALID_EXPIRY_DATE"
    assert "3 месяцев" in body["error"]["message"]


async def test_update_draft_expiry_too_soon_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={"expiry_date": too_soon_expiry_date()},
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_EXPIRY_DATE"
    await delete_request(request_id)


async def test_update_draft_expiry_too_far_fails(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={"expiry_date": too_far_expiry_date()},
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_EXPIRY_DATE"
    await delete_request(request_id)


async def test_create_request_copies_department_and_requirement(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    profile = await client.get("/api/v1/auth/profile", headers=auth_header(token))
    assert profile.status_code == 200
    department_id = profile.json()["data"]["department_id"]
    assert department_id is not None

    from app.core.database import AsyncSessionLocal
    from app.models.object import Object

    async with AsyncSessionLocal() as session:
        warehouse = await session.get(Object, catalog["warehouse_code_2"])
        assert warehouse is not None
        warehouse.long_distance = True
        await session.commit()

    try:
        status, body = await _create(
            client,
            token,
            items=[
                {
                    "product_code": catalog["product_code_2"],
                    "warehouse_code": catalog["warehouse_code_2"],
                    "quantity_requested": 500,
                    "unit": "шт",
                }
            ],
        )
        assert status == 201, body
        data = body["data"]
        assert data["department_id"] == department_id
        item = data["items"][0]
        assert item["category"] == "B"
        assert item["category_factor"] == 1.5
        assert item["long_distance"] is True
        assert item["distance_factor"] == 1.5
        assert item["requirement"] == 1125

        detail = await client.get(
            f"/api/v1/requests/{data['id']}",
            headers=auth_header(token),
        )
        assert detail.status_code == 200
        detail_item = detail.json()["data"]["items"][0]
        assert detail_item["requirement"] == 1125
        assert detail.json()["data"]["department_id"] == department_id
        await delete_request(data["id"])
    finally:
        async with AsyncSessionLocal() as session:
            warehouse = await session.get(Object, catalog["warehouse_code_2"])
            if warehouse is not None:
                warehouse.long_distance = False
                await session.commit()
