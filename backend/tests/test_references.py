from httpx import AsyncClient

from tests.conftest import AuthUser, auth_header, login_token


async def test_products_list_paginated(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/references/products",
        headers=auth_header(token),
        params={"page": 1, "limit": 1},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 1
    assert body["meta"]["total"] >= 2
    assert "code" in body["data"][0]
    assert "plant_name" in body["data"][0]


async def test_products_search(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/references/products",
        headers=auth_header(token),
        params={"search": "подшипник"},
    )
    assert response.status_code == 200, response.text
    names = [item["name"].lower() for item in response.json()["data"]]
    assert names
    assert all("подшипник" in name for name in names)


async def test_product_by_code(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        f"/api/v1/references/products/{catalog['product_code']}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["code"] == catalog["product_code"]
    assert response.json()["data"]["name"] == "Подшипник 6204ZZ"


async def test_objects_filter_warehouse(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/references/objects",
        headers=auth_header(token),
        params={"type": "warehouse"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data
    assert all(item["type"] == "warehouse" for item in data)


async def test_object_by_code(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        f"/api/v1/references/objects/{catalog['warehouse_code']}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["type"] == "warehouse"


async def test_users_list(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/references/users",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    usernames = {item["username"] for item in response.json()["data"]}
    assert test_user.username in usernames


async def test_guest_cannot_list_users(
    client: AsyncClient, guest_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, guest_user)
    response = await client.get(
        "/api/v1/references/users",
        headers=auth_header(token),
    )
    assert response.status_code == 403


async def test_departments_list(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/references/departments",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    names = {item["name"] for item in response.json()["data"]}
    assert "Тесты" in names
