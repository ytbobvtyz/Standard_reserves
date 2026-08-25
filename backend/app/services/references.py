from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.models.object import Object
from app.models.product import Product
from app.schemas.reference import (
    LastModifiedBy,
    ObjectDetail,
    ObjectListItem,
    ProductDetail,
    ProductListItem,
    RelatedProductItem,
    RelatedProductsData,
)


def to_product_list_item(product: Product) -> ProductListItem:
    return ProductListItem(
        code=product.code,
        name=product.name,
        category=product.category.strip(),
        plant_id=product.plant_id,
        plant_name=product.plant.name if product.plant else "",
        weight_kg=product.weight_kg,
        monthly_consumption=product.monthly_consumption,
        is_active=product.is_active,
        gtin=product.gtin,
        mark_control=bool(product.mark_control),
        last_modified_at=product.last_modified_at,
    )


def to_product_detail(product: Product) -> ProductDetail:
    actor = product.modified_by_user
    return ProductDetail(
        **to_product_list_item(product).model_dump(),
        description=product.description,
        second_plant_id=product.second_plant_id,
        third_plant_id=product.third_plant_id,
        parent_code=product.parent_code,
        children_code=product.children_code,
        last_modified_by=(
            LastModifiedBy(id=actor.id, full_name=actor.full_name) if actor else None
        ),
    )


def to_object_list_item(obj: Object) -> ObjectListItem:
    return ObjectListItem(
        code=obj.code,
        name=obj.name,
        city=obj.city,
        region=obj.region,
        address=obj.address,
        type=obj.type,
        erp_plant_code=obj.erp_plant_code,
        erp_warehouse_code=obj.erp_warehouse_code,
        loading_point=obj.loading_point,
        is_active=obj.is_active,
        long_distance=bool(obj.long_distance),
        last_modified_at=obj.last_modified_at,
    )


def to_object_detail(obj: Object) -> ObjectDetail:
    actor = obj.modified_by_user
    return ObjectDetail(
        **to_object_list_item(obj).model_dump(),
        last_modified_by=(
            LastModifiedBy(id=actor.id, full_name=actor.full_name) if actor else None
        ),
    )


RELATED_PRODUCTS_SQL = text("""
    WITH RECURSIVE
    ancestors AS (
        SELECT code, parent_code, children_code, name, is_active,
               'parent'::text AS relation, 1 AS level
        FROM products
        WHERE code = :code
          AND deleted_at IS NULL

        UNION ALL

        SELECT p.code, p.parent_code, p.children_code, p.name, p.is_active,
               'parent'::text, a.level + 1
        FROM products p
        JOIN ancestors a ON p.code = a.parent_code
        WHERE p.deleted_at IS NULL
          AND a.level < 20
    ),
    descendants AS (
        SELECT code, parent_code, children_code, name, is_active,
               'child'::text AS relation, 1 AS level
        FROM products
        WHERE code = :code
          AND deleted_at IS NULL

        UNION ALL

        SELECT p.code, p.parent_code, p.children_code, p.name, p.is_active,
               'child'::text, d.level + 1
        FROM products p
        JOIN descendants d ON p.code = d.children_code
        WHERE p.deleted_at IS NULL
          AND d.level < 20
    )
    SELECT code, name, relation, is_active
    FROM (
        SELECT code, name, relation, is_active, level
        FROM ancestors
        WHERE code != :code
        UNION ALL
        SELECT code, name, relation, is_active, level
        FROM descendants
        WHERE code != :code
    ) q
    ORDER BY relation DESC, code
    """)


async def get_related_products(db: AsyncSession, code: int) -> RelatedProductsData:
    product = await db.get(Product, code)
    if product is None or product.deleted_at is not None:
        raise APIError(404, "NOT_FOUND", "Продукт не найден")

    result = await db.execute(RELATED_PRODUCTS_SQL, {"code": code})
    related = [
        RelatedProductItem(
            code=row.code,
            name=row.name,
            relation=row.relation,
            is_active=row.is_active,
        )
        for row in result
    ]
    return RelatedProductsData(
        product_code=product.code,
        product_name=product.name,
        related_products=related,
    )
