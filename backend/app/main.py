import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import check_database_connection, engine
from app.core.exceptions import APIError

logger = logging.getLogger("standart_reserve")


def configure_logging() -> None:
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    if not settings.debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


configure_logging()


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
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
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


def error_body(code: str, message: str) -> dict[str, object]:
    return {"status": "error", "error": {"code": code, "message": message}}


@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    logger.warning("API error %s (%s): %s", exc.status_code, exc.code, exc.message)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message),
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if exc.status_code == 404:
        logger.info("Not found: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=404,
            content=error_body("NOT_FOUND", "Ресурс не найден"),
        )
    logger.warning(
        "HTTP %s on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("HTTP_ERROR", str(exc.detail)),
    )


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Некорректные данные запроса"
    message = str(errors[0].get("msg") or "Некорректные данные запроса")
    return message.removeprefix("Value error, ")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", _validation_message(exc)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled error on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    message = str(exc) if settings.debug else "Внутренняя ошибка сервера"
    return JSONResponse(
        status_code=500,
        content=error_body("INTERNAL_ERROR", message),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
