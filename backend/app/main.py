import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import check_database_connection, engine

logger = logging.getLogger("standart_reserve")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await check_database_connection()
        logger.info("Database connection established")
    except Exception as exc:
        logger.warning("Database is not available at startup: %s", exc)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Система управления нормативными запасами",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
