from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unknown_path_returns_json_404() -> None:
    response = client.get("/no-such-page")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "NOT_FOUND"


def test_unhandled_error_is_logged_as_500() -> None:
    @app.get("/__test/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    local = TestClient(app, raise_server_exceptions=False)
    response = local.get("/__test/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Внутренняя ошибка сервера"
