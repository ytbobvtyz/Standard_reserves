from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.normative import Normative
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.request_item_history import RequestItemHistory
from tests.conftest import AuthUser, auth_header, delete_request, login_token


def valid_expiry_date(months: int = 3) -> str:
    return Request.add_months(date.today(), months).isoformat()


def too_far_expiry_date() -> str:
    return Request.add_months(date.today(), 7).isoformat()


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


async def _create_submitted(
    client: AsyncClient, token: str, **overrides
) -> str:
    response = await client.post(
        "/api/v1/requests",
        headers=auth_header(token),
        json=request_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    request_id = response.json()["data"]["id"]
    submit = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(token),
    )
    assert submit.status_code == 200, submit.text
    return request_id


async def _pp_approve(client: AsyncClient, pp_token: str, request_id: str) -> None:
    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={"action": "approve", "comment": "Объем подтвержден"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "economy_check"


async def test_pp_approve_normative(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    pending = await client.get(
        "/api/v1/approvals/pp/pending",
        headers=auth_header(pp_token),
    )
    assert pending.status_code == 200, pending.text
    ids = {item["id"] for item in pending.json()["data"]}
    assert request_id in ids
    assert all(item.get("request_type") for item in pending.json()["data"])
    matched = next(item for item in pending.json()["data"] if item["id"] == request_id)
    assert matched["items"][0]["product_code"] == catalog["product_code"]

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={"action": "approve", "comment": "Объем подтвержден"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "economy_check"
    assert data["pp_action"] == "approve"
    assert data["comment_pp"] == "Объем подтвержден"
    assert data["pp_approved_by"]["id"] == str(pp_user.id)

    leftover = await client.get(
        "/api/v1/approvals/pp/pending",
        headers=auth_header(pp_token),
    )
    assert leftover.status_code == 200
    assert request_id not in {item["id"] for item in leftover.json()["data"]}

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(pp_token),
    )
    assert detail.json()["data"]["items"][0]["quantity_approved"] == 1000
    await delete_request(request_id)


async def test_pp_approve_one_time(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(
        client,
        commercial_token,
        request_type="one_time",
        expiry_date=None,
        comment="Разовое перемещение",
    )
    await _pp_approve(client, pp_token, request_id)
    await delete_request(request_id)


async def test_pp_edit(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    response = await client.post(
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
            "comment": "Снижаем объем на 20% из-за ограничений по заводу",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "economy_check"
    assert data["pp_action"] == "approve"
    assert data["comment_pp"] == "Снижаем объем на 20% из-за ограничений по заводу"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(pp_token),
    )
    assert detail.status_code == 200
    item = detail.json()["data"]["items"][0]
    assert item["quantity_approved"] == 800

    async with AsyncSessionLocal() as session:
        history = (
            await session.scalars(
                select(RequestItemHistory).where(
                    RequestItemHistory.field_name == "quantity_approved"
                )
            )
        ).all()
        matching = [
            row
            for row in history
            if float(row.new_value) == 800
            and row.changed_by == pp_user.id
        ]
        assert matching
        assert matching[0].comment == (
            "Снижаем объем на 20% из-за ограничений по заводу"
        )
    await delete_request(request_id)


async def test_pp_reject(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    missing = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={"action": "reject"},
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "VALIDATION_ERROR"

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "reject",
            "comment": "Нет необходимого сырья для производства",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "rejected"
    assert response.json()["data"]["pp_action"] == "reject"
    assert (
        response.json()["data"]["comment_pp"]
        == "Нет необходимого сырья для производства"
    )
    await delete_request(request_id)


async def test_edit_action_is_rejected(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "edit",
            "comment": "Больше не используется",
        },
    )
    assert response.status_code == 422
    await delete_request(request_id)


async def test_economist_approve_normative_creates_normative(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)

    pending = await client.get(
        "/api/v1/approvals/economy/pending",
        headers=auth_header(economist_token),
    )
    assert pending.status_code == 200, pending.text
    assert request_id in {item["id"] for item in pending.json()["data"]}

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Экономика приемлема"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "active"
    assert data["economy_action"] == "approve"
    assert data["comment_economy"] == "Экономика приемлема"
    assert data["economy_approved_by"]["id"] == str(economist_user.id)

    async with AsyncSessionLocal() as session:
        normatives = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).all()
        assert len(normatives) == 1
        normative = normatives[0]
        assert normative.product_code == catalog["product_code"]
        assert normative.warehouse_code == catalog["warehouse_code"]
        assert float(normative.quantity) == 1000
        assert normative.client_name == "ООО Ромашка"
        assert normative.category.strip() == "A"
    await delete_request(request_id)


async def test_economist_approve_one_time(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(
        client,
        commercial_token,
        request_type="one_time",
        expiry_date=None,
        comment="Разовое перемещение",
    )
    await _pp_approve(client, pp_token, request_id)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Доставка экономически обоснована"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "approved"

    async with AsyncSessionLocal() as session:
        normatives = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).all()
        assert normatives == []
    await delete_request(request_id)


async def test_economist_approve_with_quantity_change(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "approve",
            "items": [
                {
                    "product_code": catalog["product_code"],
                    "warehouse_code": catalog["warehouse_code"],
                    "quantity_approved": 600,
                }
            ],
            "comment": "Снижаем до 600 шт. Хранение дороже срочной доставки",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "active"
    assert response.json()["data"]["economy_action"] == "approve"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(economist_token),
    )
    assert detail.json()["data"]["items"][0]["quantity_approved"] == 600

    async with AsyncSessionLocal() as session:
        item_ids = (
            await session.scalars(
                select(RequestItem.id).where(RequestItem.request_id == request_id)
            )
        ).all()
        history = (
            await session.scalars(
                select(RequestItemHistory).where(
                    RequestItemHistory.request_item_id.in_(item_ids),
                    RequestItemHistory.changed_by == economist_user.id,
                )
            )
        ).all()
        assert history
        assert float(history[0].new_value) == 600
    await delete_request(request_id)


async def test_economist_reject(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "reject",
            "comment": "Хранение экономически нецелесообразно",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "rejected"
    assert response.json()["data"]["comment_economy"] == (
        "Хранение экономически нецелесообразно"
    )
    await delete_request(request_id)


async def test_non_pp_cannot_approve(
    client: AsyncClient,
    test_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    request_id = await _create_submitted(client, commercial_token)

    pending = await client.get(
        "/api/v1/approvals/pp/pending",
        headers=auth_header(commercial_token),
    )
    assert pending.status_code == 403

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(commercial_token),
        json={"action": "approve"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    await delete_request(request_id)


async def test_cannot_approve_wrong_status(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    created = await client.post(
        "/api/v1/requests",
        headers=auth_header(commercial_token),
        json=request_payload(),
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={"action": "approve"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATUS"
    await delete_request(request_id)


async def test_pp_edit_rejects_non_positive_quantity(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "approve",
            "items": [
                {
                    "product_code": catalog["product_code"],
                    "warehouse_code": catalog["warehouse_code"],
                    "quantity_approved": 0,
                }
            ],
            "comment": "Ноль недопустим",
        },
    )
    assert response.status_code == 422
    await delete_request(request_id)


async def test_pp_edit_visible_to_economist(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)

    edited = await client.post(
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
            "comment": "Снижаем объем",
        },
    )
    assert edited.status_code == 200, edited.text

    pending = await client.get(
        "/api/v1/approvals/economy/pending",
        headers=auth_header(economist_token),
    )
    assert pending.status_code == 200, pending.text
    matched = next(item for item in pending.json()["data"] if item["id"] == request_id)
    assert matched["items"][0]["quantity_requested"] == 1000
    assert matched["items"][0]["quantity_approved"] == 800
    await delete_request(request_id)


async def test_final_approve_exposes_quantity_approved(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)

    edited = await client.post(
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
            "comment": "Снижаем объем",
        },
    )
    assert edited.status_code == 200, edited.text

    approved = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Экономика приемлема"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "active"

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(economist_token),
    )
    assert detail.status_code == 200
    item = detail.json()["data"]["items"][0]
    assert item["quantity_requested"] == 1000
    assert item["quantity_approved"] == 800

    async with AsyncSessionLocal() as session:
        normative = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).one()
        assert float(normative.quantity) == 800
    await delete_request(request_id)


async def test_pp_edit_expiry_date_success(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)
    new_expiry = valid_expiry_date(5)

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "approve",
            "expiry_date": new_expiry,
            "comment": "Сдвинули срок",
        },
    )
    assert response.status_code == 200, response.text
    assert "Срок действия:" in response.json()["data"]["comment_pp"]

    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(pp_token),
    )
    assert detail.json()["data"]["expiry_date"] == new_expiry
    history_comments = [
        entry.get("comment") or ""
        for entry in detail.json()["data"]["history"]
    ]
    assert any("Срок действия:" in comment for comment in history_comments)
    await delete_request(request_id)


async def test_pp_edit_expiry_date_too_far_fails(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(client, commercial_token)

    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "approve",
            "expiry_date": too_far_expiry_date(),
            "comment": "Слишком долго",
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_EXPIRY_DATE"
    await delete_request(request_id)


async def test_economy_approve_expiry_date_too_far_fails(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "approve",
            "expiry_date": too_far_expiry_date(),
            "comment": "Слишком долго",
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert (
        response.json()["error"]["message"]
        == "Дата окончания не может быть позже текущей"
    )
    await delete_request(request_id)


async def test_economy_edit_can_reduce_expiry_date(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(
        client, commercial_token, expiry_date=valid_expiry_date(3)
    )
    await _pp_approve(client, pp_token, request_id)
    new_expiry = valid_expiry_date(1)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "approve",
            "expiry_date": new_expiry,
            "comment": "Уменьшаем срок",
        },
    )
    assert response.status_code == 200, response.text
    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(economist_token),
    )
    assert detail.json()["data"]["expiry_date"] == new_expiry
    await delete_request(request_id)


async def test_economy_edit_cannot_increase_expiry_date(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(
        client, commercial_token, expiry_date=valid_expiry_date(3)
    )
    await _pp_approve(client, pp_token, request_id)

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "approve",
            "expiry_date": valid_expiry_date(5),
            "comment": "Пытаемся увеличить",
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert (
        response.json()["error"]["message"]
        == "Дата окончания не может быть позже текущей"
    )
    await delete_request(request_id)


async def test_economy_edit_cannot_set_expiry_in_the_past(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)
    past = (date.today() - timedelta(days=1)).isoformat()

    response = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={
            "action": "approve",
            "expiry_date": past,
            "comment": "Вчера",
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert (
        response.json()["error"]["message"]
        == "Дата окончания не может быть раньше сегодняшнего дня"
    )
    await delete_request(request_id)


async def test_active_expiry_can_be_reduced(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(
        client, commercial_token, expiry_date=valid_expiry_date(3)
    )
    await _pp_approve(client, pp_token, request_id)
    approved = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Экономика приемлема"},
    )
    assert approved.status_code == 200, approved.text
    new_expiry = valid_expiry_date(1)
    response = await client.patch(
        f"/api/v1/requests/{request_id}/expiry-date",
        headers=auth_header(commercial_token),
        json={"expiry_date": new_expiry},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["expiry_date"] == new_expiry
    async with AsyncSessionLocal() as session:
        normative = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).one()
        assert normative.expiry_date.isoformat() == new_expiry
    await delete_request(request_id)


async def test_active_expiry_cannot_be_increased(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(
        client, commercial_token, expiry_date=valid_expiry_date(3)
    )
    await _pp_approve(client, pp_token, request_id)
    approved = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Экономика приемлема"},
    )
    assert approved.status_code == 200, approved.text
    response = await client.patch(
        f"/api/v1/requests/{request_id}/expiry-date",
        headers=auth_header(commercial_token),
        json={"expiry_date": valid_expiry_date(5)},
    )
    assert response.status_code == 400, response.text
    assert (
        response.json()["error"]["message"]
        == "Дата окончания не может быть позже текущей"
    )
    await delete_request(request_id)


async def test_delete_active_keeps_normatives(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    economist_token = await login_token(client, economist_user)
    request_id = await _create_submitted(client, commercial_token)
    await _pp_approve(client, pp_token, request_id)
    approved = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "Экономика приемлема"},
    )
    assert approved.status_code == 200, approved.text
    response = await client.delete(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(commercial_token),
    )
    assert response.status_code == 400
    async with AsyncSessionLocal() as session:
        normative = (
            await session.scalars(
                select(Normative).where(Normative.request_id == request_id)
            )
        ).one()
        assert normative.deleted_at is None
    await delete_request(request_id)
