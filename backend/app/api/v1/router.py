from fastapi import APIRouter

from app.api.v1.endpoints import (
    approvals,
    auth,
    logistics_normative,
    logistics_one_time,
    normatives,
    products,
    references,
    requests,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(references.router)
api_router.include_router(products.router)
api_router.include_router(requests.router)
api_router.include_router(approvals.router)
api_router.include_router(logistics_normative.router)
api_router.include_router(logistics_one_time.router)
api_router.include_router(normatives.router)


@api_router.get("/status")
async def api_status() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}
