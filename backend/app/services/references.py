from app.models.product import Product
from app.schemas.reference import ProductDetail, ProductListItem


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
    )


def to_product_detail(product: Product) -> ProductDetail:
    return ProductDetail(
        **to_product_list_item(product).model_dump(),
        description=product.description,
        second_plant_id=product.second_plant_id,
        third_plant_id=product.third_plant_id,
        parent_code=product.parent_code,
        children_code=product.children_code,
    )
