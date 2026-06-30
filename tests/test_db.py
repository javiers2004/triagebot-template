import pytest

from app import db


@pytest.fixture()
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    db.init_db()


def _create(title="Título", description="Desc", category="bug", priority="P1", tags=None):
    return db.create_ticket(title, description, category, priority, tags or [])


# ---------------------------------------------------------------------------
# create_ticket
# ---------------------------------------------------------------------------


def test_create_returns_dict_with_id(database):
    ticket = _create()
    assert isinstance(ticket["id"], int) and ticket["id"] > 0


def test_create_stores_all_fields(database):
    ticket = _create(title="T", description="D", category="bug", priority="P2", tags=["a"])
    assert ticket["title"] == "T"
    assert ticket["description"] == "D"
    assert ticket["category"] == "bug"
    assert ticket["priority"] == "P2"
    assert ticket["tags"] == ["a"]


def test_create_default_status_open(database):
    assert _create()["status"] == "open"


def test_create_empty_tags(database):
    assert _create(tags=[])["tags"] == []


def test_create_multiple_tags(database):
    tags = ["login", "auth", "crash"]
    assert _create(tags=tags)["tags"] == tags


def test_create_timestamps_equal_on_creation(database):
    t = _create()
    assert t["created_at"] == t["updated_at"]


def test_create_ids_unique(database):
    ids = [_create(title=f"T{i}")["id"] for i in range(5)]
    assert len(set(ids)) == 5


def test_create_all_categories(database):
    for cat in ("bug", "feature_request", "question", "urgent"):
        t = _create(category=cat)
        assert t["category"] == cat


def test_create_all_priorities(database):
    for p in ("P1", "P2", "P3"):
        t = _create(priority=p)
        assert t["priority"] == p


# ---------------------------------------------------------------------------
# get_ticket
# ---------------------------------------------------------------------------


def test_get_ticket_by_id(database):
    created = _create(title="Buscar esto")
    found = db.get_ticket(created["id"])
    assert found["id"] == created["id"]
    assert found["title"] == "Buscar esto"


def test_get_ticket_none_for_missing(database):
    assert db.get_ticket(9999) is None


def test_get_ticket_returns_correct_tags(database):
    tags = ["x", "y", "z"]
    created = _create(tags=tags)
    assert db.get_ticket(created["id"])["tags"] == tags


# ---------------------------------------------------------------------------
# list_tickets
# ---------------------------------------------------------------------------


def test_list_empty(database):
    assert db.list_tickets() == []


def test_list_returns_all(database):
    for i in range(3):
        _create(title=f"T{i}")
    assert len(db.list_tickets()) == 3


def test_list_ordered_newest_first(database):
    _create(title="Primero")
    _create(title="Segundo")
    _create(title="Tercero")
    titles = [t["title"] for t in db.list_tickets()]
    assert titles == ["Tercero", "Segundo", "Primero"]


def test_list_filter_category(database):
    _create(category="bug")
    _create(category="question")
    results = db.list_tickets(category="bug")
    assert len(results) == 1 and results[0]["category"] == "bug"


def test_list_filter_priority(database):
    _create(priority="P1")
    _create(priority="P3")
    results = db.list_tickets(priority="P3")
    assert len(results) == 1 and results[0]["priority"] == "P3"


def test_list_filter_status(database):
    t = _create()
    db.update_ticket(t["id"], status="closed")
    assert db.list_tickets(status="open") == []
    assert len(db.list_tickets(status="closed")) == 1


def test_list_filter_category_and_priority(database):
    _create(title="Bug P1", category="bug", priority="P1")
    _create(title="Bug P2", category="bug", priority="P2")
    _create(title="Question P1", category="question", priority="P1")
    results = db.list_tickets(category="bug", priority="P1")
    assert len(results) == 1 and results[0]["title"] == "Bug P1"


def test_list_filter_all_three(database):
    t = _create(category="urgent", priority="P1")
    db.update_ticket(t["id"], status="in_progress")
    _create(category="urgent", priority="P1")  # status=open
    results = db.list_tickets(category="urgent", priority="P1", status="in_progress")
    assert len(results) == 1


def test_list_no_match_returns_empty(database):
    _create(category="bug")
    assert db.list_tickets(category="urgent") == []


# ---------------------------------------------------------------------------
# update_ticket
# ---------------------------------------------------------------------------


def test_update_status(database):
    t = _create()
    assert db.update_ticket(t["id"], status="closed")["status"] == "closed"


def test_update_priority(database):
    t = _create(priority="P1")
    assert db.update_ticket(t["id"], priority="P3")["priority"] == "P3"


def test_update_both_fields(database):
    t = _create()
    updated = db.update_ticket(t["id"], status="in_progress", priority="P2")
    assert updated["status"] == "in_progress"
    assert updated["priority"] == "P2"


def test_update_no_fields_returns_ticket(database):
    t = _create(priority="P1")
    unchanged = db.update_ticket(t["id"])
    assert unchanged["status"] == "open"
    assert unchanged["priority"] == "P1"


def test_update_nonexistent_returns_none(database):
    assert db.update_ticket(9999, status="closed") is None


def test_update_does_not_change_other_fields(database):
    t = _create(title="Intacto", category="urgent", tags=["keep"])
    updated = db.update_ticket(t["id"], status="closed")
    assert updated["title"] == "Intacto"
    assert updated["category"] == "urgent"
    assert updated["tags"] == ["keep"]


def test_update_multiple_times(database):
    t = _create()
    db.update_ticket(t["id"], status="in_progress")
    db.update_ticket(t["id"], status="closed")
    final = db.get_ticket(t["id"])
    assert final["status"] == "closed"


def test_update_visible_in_list(database):
    t = _create()
    db.update_ticket(t["id"], status="closed")
    open_list = db.list_tickets(status="open")
    closed_list = db.list_tickets(status="closed")
    assert all(x["id"] != t["id"] for x in open_list)
    assert any(x["id"] == t["id"] for x in closed_list)


def test_update_status_resolved(database):
    t = _create()
    updated = db.update_ticket(t["id"], status="resolved")
    assert updated["status"] == "resolved"


def test_list_filter_status_resolved(database):
    t = _create()
    db.update_ticket(t["id"], status="resolved")
    assert len(db.list_tickets(status="resolved")) == 1
    assert db.list_tickets(status="open") == []


# ---------------------------------------------------------------------------
# assignees
# ---------------------------------------------------------------------------


def test_create_default_assignees_empty(database):
    assert _create()["assignees"] == []


def test_create_with_assignees(database):
    t = db.create_ticket("T", "D", "bug", "P1", [], assignees=["alice", "bob"])
    assert t["assignees"] == ["alice", "bob"]


def test_update_assignees(database):
    t = _create()
    updated = db.update_ticket(t["id"], assignees=["alice"])
    assert updated["assignees"] == ["alice"]


def test_update_assignees_empty_list(database):
    t = db.create_ticket("T", "D", "bug", "P1", [], assignees=["alice"])
    updated = db.update_ticket(t["id"], assignees=[])
    assert updated["assignees"] == []


def test_update_assignees_multiple(database):
    t = _create()
    updated = db.update_ticket(t["id"], assignees=["alice", "bob", "carlos"])
    assert updated["assignees"] == ["alice", "bob", "carlos"]


def test_update_assignees_none_does_not_clear(database):
    t = db.create_ticket("T", "D", "bug", "P1", [], assignees=["alice"])
    updated = db.update_ticket(t["id"], assignees=None)
    assert updated["assignees"] == ["alice"]


def test_get_ticket_returns_assignees(database):
    t = db.create_ticket("T", "D", "bug", "P1", [], assignees=["dev1"])
    fetched = db.get_ticket(t["id"])
    assert fetched["assignees"] == ["dev1"]
