import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    return TestClient(app)


def _fake(category="bug", priority="P1", tags=None):
    return {"category": category, "priority": priority, "tags": tags or []}


def _post(client, title="Ticket de prueba", description="Descripción del ticket"):
    return client.post("/tickets", json={"title": title, "description": description})


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_health_status_code_200(client):
    assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# GET / (página principal HTML)
# ---------------------------------------------------------------------------


def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_index_filter_by_category(client):
    response = client.get("/", params={"category": "bug"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_index_filter_by_priority(client):
    assert client.get("/", params={"priority": "P1"}).status_code == 200


def test_index_filter_by_status(client):
    assert client.get("/", params={"status": "open"}).status_code == 200


def test_index_all_filters_combined(client):
    assert client.get("/", params={"category": "bug", "priority": "P1", "status": "open"}).status_code == 200


# ---------------------------------------------------------------------------
# POST /tickets — respuesta y campos
# ---------------------------------------------------------------------------


def test_post_ticket_returns_201(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    assert _post(client).status_code == 201


def test_post_ticket_returns_id(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = _post(client).json()
    assert isinstance(data["id"], int)
    assert data["id"] > 0


def test_post_ticket_stores_title_and_description(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = client.post("/tickets", json={"title": "Mi título", "description": "Mi descripción"}).json()
    assert data["title"] == "Mi título"
    assert data["description"] == "Mi descripción"


def test_post_ticket_title_stripped(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = client.post("/tickets", json={"title": "  Espacios  ", "description": "desc"}).json()
    assert data["title"] == "Espacios"


def test_post_ticket_default_status_open(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    assert _post(client).json()["status"] == "open"


def test_post_ticket_tags_returned_as_list(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(tags=["auth", "mobile"]))
    assert _post(client).json()["tags"] == ["auth", "mobile"]


def test_post_ticket_empty_tags(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(tags=[]))
    assert _post(client).json()["tags"] == []


def test_post_ticket_timestamps_present(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = _post(client).json()
    assert "created_at" in data and "updated_at" in data


def test_post_ticket_created_equals_updated_on_creation(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = _post(client).json()
    assert data["created_at"] == data["updated_at"]


def test_post_ticket_ids_are_unique(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    ids = [_post(client, title=f"Ticket único {i}").json()["id"] for i in range(5)]
    assert len(set(ids)) == 5


def test_post_duplicate_ticket_returns_409(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    _post(client)
    r = _post(client)
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /tickets — validación de entrada (límites exactos)
# ---------------------------------------------------------------------------


def test_post_title_200_chars_passes(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    response = client.post("/tickets", json={"title": "x" * 200, "description": "desc"})
    assert response.status_code == 201


def test_post_title_201_chars_fails(client):
    assert client.post("/tickets", json={"title": "x" * 201, "description": "desc"}).status_code == 422


def test_post_description_5000_chars_passes(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    response = client.post("/tickets", json={"title": "titulo", "description": "x" * 5000})
    assert response.status_code == 201


def test_post_description_5001_chars_fails(client):
    assert client.post("/tickets", json={"title": "titulo", "description": "x" * 5001}).status_code == 422


# ---------------------------------------------------------------------------
# GET /tickets
# ---------------------------------------------------------------------------


def test_list_tickets_empty_initially(client):
    assert client.get("/tickets").json() == []


def test_list_tickets_returns_all(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    for i in range(4):
        _post(client, title=f"Ticket {i}")
    assert len(client.get("/tickets").json()) == 4


def test_list_tickets_ordered_newest_first(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    _post(client, title="Primero")
    _post(client, title="Segundo")
    tickets = client.get("/tickets").json()
    assert tickets[0]["title"] == "Segundo"
    assert tickets[1]["title"] == "Primero"


def test_list_tickets_filter_category(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(category="bug"))
    _post(client, title="Bug")
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(category="question"))
    _post(client, title="Pregunta")

    bugs = client.get("/tickets", params={"category": "bug"}).json()
    assert len(bugs) == 1 and bugs[0]["category"] == "bug"


def test_list_tickets_filter_priority(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(priority="P1"))
    _post(client, title="Urgente")
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(priority="P3"))
    _post(client, title="Baja")

    results = client.get("/tickets", params={"priority": "P1"}).json()
    assert len(results) == 1 and results[0]["priority"] == "P1"


def test_list_tickets_filter_status(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "closed"})

    assert len(client.get("/tickets", params={"status": "open"}).json()) == 0
    assert len(client.get("/tickets", params={"status": "closed"}).json()) == 1


def test_list_tickets_filter_no_match_returns_empty(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(category="bug"))
    _post(client)
    assert client.get("/tickets", params={"category": "urgent"}).json() == []


def test_list_tickets_all_categories(client, monkeypatch):
    for cat in ("bug", "feature_request", "question", "urgent"):
        monkeypatch.setattr("app.classifier.classify_ticket", lambda *_, c=cat: _fake(category=c))
        _post(client, title=f"Ticket {cat}")

    for cat in ("bug", "feature_request", "question", "urgent"):
        results = client.get("/tickets", params={"category": cat}).json()
        assert len(results) == 1


# ---------------------------------------------------------------------------
# PATCH /tickets/{id}
# ---------------------------------------------------------------------------


def test_patch_returns_200(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    assert client.patch(f"/tickets/{tid}", json={"status": "closed"}).status_code == 200


def test_patch_nonexistent_returns_404(client):
    assert client.patch("/tickets/9999", json={"status": "closed"}).status_code == 404


def test_patch_invalid_status_returns_422(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    assert client.patch(f"/tickets/{tid}", json={"status": "inventado"}).status_code == 422


def test_patch_invalid_priority_returns_422(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    assert client.patch(f"/tickets/{tid}", json={"priority": "P9"}).status_code == 422


def test_patch_status_only_keeps_priority(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake(priority="P1"))
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"status": "in_progress"}).json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "P1"


def test_patch_priority_only_keeps_status(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"priority": "P2"}).json()
    assert data["priority"] == "P2"
    assert data["status"] == "open"


def test_patch_updated_at_changes(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    created = _post(client).json()
    updated = client.patch(f"/tickets/{created['id']}", json={"status": "closed"}).json()
    assert updated["updated_at"] >= created["updated_at"]


def test_patch_title_not_modified(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client, title="Sin cambios").json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"status": "closed"}).json()
    assert data["title"] == "Sin cambios"


@pytest.mark.parametrize("status", ["open", "in_progress", "resolved", "closed"])
def test_patch_all_valid_statuses(client, monkeypatch, status):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"status": status}).json()
    assert data["status"] == status


@pytest.mark.parametrize("priority", ["P1", "P2", "P3"])
def test_patch_all_valid_priorities(client, monkeypatch, priority):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"priority": priority}).json()
    assert data["priority"] == priority


def test_patch_assignees(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"assignees": ["alice", "bob"]}).json()
    assert data["assignees"] == ["alice", "bob"]


def test_patch_assignees_empty_list(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["alice"]})
    data = client.patch(f"/tickets/{tid}", json={"assignees": []}).json()
    assert data["assignees"] == []


def test_post_ticket_default_assignees_empty(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    data = _post(client).json()
    assert data["assignees"] == []


def test_patch_resolved_status(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    data = client.patch(f"/tickets/{tid}", json={"status": "resolved"}).json()
    assert data["status"] == "resolved"


def test_list_tickets_filter_resolved(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "resolved"})
    assert len(client.get("/tickets", params={"status": "resolved"}).json()) == 1
    assert len(client.get("/tickets", params={"status": "open"}).json()) == 0


def test_list_tickets_filter_by_assignee(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client, title="Asignado a Técnico").json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["Técnico"]})
    _post(client, title="Sin asignar")

    results = client.get("/tickets", params={"assignee": "Técnico"}).json()
    assert len(results) == 1 and results[0]["title"] == "Asignado a Técnico"


def test_list_tickets_filter_assignee_no_match(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["Técnico"]})
    assert client.get("/tickets", params={"assignee": "Tester"}).json() == []


# ---------------------------------------------------------------------------
# PATCH /partials/tickets/{id}  — form endpoint (HTML)
# ---------------------------------------------------------------------------


def test_html_patch_returns_html(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    r = client.patch(f"/partials/tickets/{tid}", data={"status": "open"})
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_html_patch_assignees_comma_separated(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    r = client.patch(f"/partials/tickets/{tid}", data={"assignees": "Alice, Bob"})
    assert r.status_code == 200
    assert "Alice" in r.text
    assert "Bob" in r.text


def test_html_patch_assignees_single(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    r = client.patch(f"/partials/tickets/{tid}", data={"assignees": "Alice"})
    assert "Alice" in r.text


def test_html_patch_assignees_cleared_by_empty(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/partials/tickets/{tid}", data={"assignees": "Alice"})
    r = client.patch(f"/partials/tickets/{tid}", data={"assignees": ""})
    assert "Alice" not in r.text


def test_html_patch_assignees_strips_whitespace(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    r = client.patch(f"/partials/tickets/{tid}", data={"assignees": "  Alice  ,  Bob  "})
    assert "Alice" in r.text
    assert "Bob" in r.text


def test_html_patch_status_resolved(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    r = client.patch(f"/partials/tickets/{tid}", data={"status": "resolved"})
    assert "resolved" in r.text


def test_html_patch_nonexistent_returns_404(client):
    r = client.patch("/partials/tickets/9999", data={"status": "open"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /partials/tickets — filtro por asignado (HTML)
# ---------------------------------------------------------------------------


def test_partials_filter_by_assignee(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client, title="Ticket asignado").json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["Alice"]})
    _post(client, title="Sin asignar")

    r = client.get("/partials/tickets", params={"assignee": "Alice"})
    assert r.status_code == 200
    assert "Ticket asignado" in r.text
    assert "Sin asignar" not in r.text


def test_partials_filter_assignee_no_match_shows_empty(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client).json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["Alice"]})

    r = client.get("/partials/tickets", params={"assignee": "Bob"})
    assert r.status_code == 200
    assert "No hay tickets" in r.text


# ---------------------------------------------------------------------------
# GET / — filtro por asignado en la página principal
# ---------------------------------------------------------------------------


def test_index_filter_by_assignee_returns_html(client, monkeypatch):
    monkeypatch.setattr("app.classifier.classify_ticket", lambda *_: _fake())
    tid = _post(client, title="Asignado").json()["id"]
    client.patch(f"/tickets/{tid}", json={"assignees": ["Alice"]})

    r = client.get("/", params={"assignee": "Alice"})
    assert r.status_code == 200
    assert "Asignado" in r.text
