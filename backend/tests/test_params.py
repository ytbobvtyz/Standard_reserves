from httpx import AsyncClient

from tests.conftest import AuthUser, auth_header, login_token


async def test_get_params_authenticated(
    client: AsyncClient, test_user: AuthUser
) -> None:
    token = await login_token(client, test_user)
    response = await client.get("/api/v1/params", headers=auth_header(token))
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["category_a"] == 1
    assert data["category_b"] == 1.5
    assert data["category_c"] == 2
    assert data["remote_warehouse"] == 1.5
    assert data["pallet_multiple"] is False


async def test_admin_params_forbidden_for_commercial(
    client: AsyncClient, test_user: AuthUser
) -> None:
    token = await login_token(client, test_user)
    response = await client.put(
        "/api/v1/admin/params",
        headers=auth_header(token),
        json={
            "category_a": 1,
            "category_b": 1.5,
            "category_c": 2,
            "remote_warehouse": 1.5,
            "pallet_multiple": True,
        },
    )
    assert response.status_code == 403


async def test_update_params_validation(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    too_high = await client.put(
        "/api/v1/admin/params",
        headers=auth_header(token),
        json={
            "category_a": 3.1,
            "category_b": 1.5,
            "category_c": 2,
            "remote_warehouse": 1.5,
            "pallet_multiple": False,
        },
    )
    assert too_high.status_code == 422

    bad_step = await client.put(
        "/api/v1/admin/params",
        headers=auth_header(token),
        json={
            "category_a": 1.15,
            "category_b": 1.5,
            "category_c": 2,
            "remote_warehouse": 1.5,
            "pallet_multiple": False,
        },
    )
    assert bad_step.status_code == 422


async def test_update_params_saves_user_and_timestamp(
    client: AsyncClient, logistics_user: AuthUser
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.put(
        "/api/v1/admin/params",
        headers=auth_header(token),
        json={
            "category_a": 1.2,
            "category_b": 1.6,
            "category_c": 2.1,
            "remote_warehouse": 1.8,
            "pallet_multiple": True,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["category_a"] == 1.2
    assert data["category_b"] == 1.6
    assert data["category_c"] == 2.1
    assert data["remote_warehouse"] == 1.8
    assert data["pallet_multiple"] is True
    assert data["last_modified_by"]["id"] == str(logistics_user.id)
    assert data["last_modified_by"]["username"] == logistics_user.username
    assert data["last_modified_at"] is not None
