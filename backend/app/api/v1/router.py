from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)


@api_router.get("/status")
async def api_status() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}
