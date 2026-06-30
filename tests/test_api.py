import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    return TestClient(app)


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_update_nonexistent_ticket_returns_404(client):
    response = client.patch("/tickets/99999", json={"status": "closed"})
    assert response.status_code == 404


def test_update_ticket_with_invalid_status_returns_422(client):
    response = client.patch("/tickets/1", json={"status": "inventado"})
    assert response.status_code == 422
