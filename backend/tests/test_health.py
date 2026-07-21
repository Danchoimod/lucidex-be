from fastapi.testclient import TestClient

from src.main import app


def test_health_check() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok"},
        "message": "Lucidex API is healthy.",
        "error_code": None,
    }
