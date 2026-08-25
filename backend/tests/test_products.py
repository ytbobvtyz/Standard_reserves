from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.product import Product
from tests.conftest import AuthUser, auth_header, login_token

PARENT_CODE = 18101
MIDDLE_CODE = 18102
CHILD_CODE = 18103
LONE_CODE = 18110


async def _cleanup_related() -> None:
    async with AsyncSessionLocal() as session:
        for code in (PARENT_CODE, MIDDLE_CODE, CHILD_CODE):
            product = await session.get(Product, code)
            if product is not None:
                product.parent_code = None
                product.children_code = None
        await session.flush()
        await session.execute(
            delete(Product).where(
                Product.code.in_([PARENT_CODE, MIDDLE_CODE, CHILD_CODE, LONE_CODE])
            )
        )
        await session.commit()


async def _seed_related_chain(catalog: dict[str, int]) -> None:
    await _cleanup_related()
    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                code=PARENT_CODE,
                name="Старый артикул цепочки",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                monthly_consumption=Decimal("1000.00"),
                is_active=False,
            )
        )
        session.add(
            Product(
                code=MIDDLE_CODE,
                name="Текущий артикул цепочки",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                monthly_consumption=Decimal("1000.00"),
                is_active=True,
            )
        )
        session.add(
            Product(
                code=CHILD_CODE,
                name="Новый артикул цепочки",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2550"),
                monthly_consumption=Decimal("800.00"),
                is_active=True,
            )
        )
        await session.flush()
        parent = await session.get(Product, PARENT_CODE)
        middle = await session.get(Product, MIDDLE_CODE)
        child = await session.get(Product, CHILD_CODE)
        assert parent is not None
        assert middle is not None
        assert child is not None
        parent.children_code = MIDDLE_CODE
        middle.parent_code = PARENT_CODE
        middle.children_code = CHILD_CODE
        child.parent_code = MIDDLE_CODE
        await session.commit()


async def test_related_products_chain_up_and_down(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _seed_related_chain(catalog)
    token = await login_token(client, test_user)
    try:
        response = await client.get(
            f"/api/v1/products/{MIDDLE_CODE}/related",
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["product_code"] == MIDDLE_CODE
        assert data["product_name"] == "Текущий артикул цепочки"
        related = {item["code"]: item for item in data["related_products"]}
        assert PARENT_CODE in related
        assert CHILD_CODE in related
        assert related[PARENT_CODE]["relation"] == "parent"
        assert related[PARENT_CODE]["is_active"] is False
        assert related[CHILD_CODE]["relation"] == "child"
        assert related[CHILD_CODE]["is_active"] is True

        from_parent = await client.get(
            f"/api/v1/products/{PARENT_CODE}/related",
            headers=auth_header(token),
        )
        assert from_parent.status_code == 200
        parent_related = {
            item["code"]: item["relation"]
            for item in from_parent.json()["data"]["related_products"]
        }
        assert parent_related[MIDDLE_CODE] == "child"
        assert parent_related[CHILD_CODE] == "child"

        from_child = await client.get(
            f"/api/v1/products/{CHILD_CODE}/related",
            headers=auth_header(token),
        )
        assert from_child.status_code == 200
        child_related = {
            item["code"]: item["relation"]
            for item in from_child.json()["data"]["related_products"]
        }
        assert child_related[MIDDLE_CODE] == "parent"
        assert child_related[PARENT_CODE] == "parent"
    finally:
        await _cleanup_related()


async def test_related_products_not_found(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/products/999999/related",
        headers=auth_header(token),
    )
    assert response.status_code == 404


async def test_related_products_empty_chain(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _cleanup_related()
    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                code=LONE_CODE,
                name="Артикул без родственников",
                category="B",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("1.0000"),
                is_active=True,
            )
        )
        await session.commit()
    token = await login_token(client, test_user)
    try:
        response = await client.get(
            f"/api/v1/products/{LONE_CODE}/related",
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["product_code"] == LONE_CODE
        assert data["related_products"] == []
    finally:
        await _cleanup_related()


async def test_products_include_analogs(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _seed_related_chain(catalog)
    token = await login_token(client, test_user)
    try:
        response = await client.get(
            "/api/v1/references/products",
            headers=auth_header(token),
            params={
                "search": str(MIDDLE_CODE),
                "include_analogs": True,
                "is_active": True,
            },
        )
        assert response.status_code == 200, response.text
        items = response.json()["data"]
        by_code = {item["code"]: item for item in items}
        assert MIDDLE_CODE in by_code
        assert by_code[MIDDLE_CODE]["is_analog"] is False
        assert CHILD_CODE in by_code
        assert by_code[CHILD_CODE]["is_analog"] is True
        assert PARENT_CODE not in by_code

        without = await client.get(
            "/api/v1/references/products",
            headers=auth_header(token),
            params={"search": str(MIDDLE_CODE), "is_active": True},
        )
        codes = [item["code"] for item in without.json()["data"]]
        assert MIDDLE_CODE in codes
        assert CHILD_CODE not in codes
    finally:
        await _cleanup_related()
