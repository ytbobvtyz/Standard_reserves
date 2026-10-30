import asyncio

from app.core.database import AsyncSessionLocal
from app.services.logistics_normative import get_dashboard


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await get_dashboard(
            db, warehouse_code=2001, filter_mode="all", unit="шт"
        )
    shown = 0
    nonzero = 0
    samples: list[tuple] = []
    for warehouse in result.data:
        for item in warehouse.deficit_items:
            shown += 1
            parts = (item.no_ready, item.ready, item.collected, item.on_way)
            if any(part != 0 for part in parts):
                nonzero += 1
                if len(samples) < 5:
                    samples.append(
                        (
                            item.product_code,
                            float(item.available),
                            float(item.no_ready),
                            float(item.ready),
                            float(item.collected),
                            float(item.on_way),
                            float(item.plan),
                        )
                    )
    print("shown", shown, "nonzero_parts", nonzero)
    for row in samples:
        print(row)
    target = next(
        (
            item
            for warehouse in result.data
            for item in warehouse.deficit_items
            if item.product_code == 2230527
        ),
        None,
    )
    if target is not None:
        print(target.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
