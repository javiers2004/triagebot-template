import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta

_PRIORITY_DEADLINE: dict[str, timedelta] = {
    "P1": timedelta(hours=0),
    "P2": timedelta(days=1),
    "P3": timedelta(days=2),
}

_initialized: set[str] = set()

_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""


def _db_path() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///triagebot.db")
    return url.removeprefix("sqlite:///")


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if path not in _initialized:
        conn.execute(_CREATE_TABLE)
        conn.commit()
        _initialized.add(path)
    return conn


def init_db() -> None:
    with get_connection():
        pass


def create_ticket(
    title: str, description: str, category: str, priority: str, tags: list[str]
) -> dict:
    now = datetime.now(UTC).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO tickets
               (title, description, category, priority, tags, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'open', ?, ?)""",
            (title, description, category, priority, json.dumps(tags), now, now),
        )
        conn.commit()
        ticket_id = cursor.lastrowid
    return get_ticket(ticket_id)


def get_ticket(ticket_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_tickets(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    overdue: bool = False,
) -> list[dict]:
    conditions: list[str] = []
    params: list[str] = []
    if category is not None:
        conditions.append("category = ?")
        params.append(category)
    if priority is not None:
        conditions.append("priority = ?")
        params.append(priority)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)

    query = "SELECT * FROM tickets"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    tickets = [_row_to_dict(r) for r in rows]
    if overdue:
        now = datetime.now(UTC).isoformat()
        tickets = [t for t in tickets if t["due_date"] <= now]
    return tickets


def update_ticket(
    ticket_id: int,
    status: str | None = None,
    priority: str | None = None,
) -> dict | None:
    updates: list[str] = []
    params: list = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)

    if not updates:
        return get_ticket(ticket_id)

    now = datetime.now(UTC).isoformat()
    updates.append("updated_at = ?")
    params.append(now)
    params.append(ticket_id)

    with get_connection() as conn:
        conn.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    return get_ticket(ticket_id)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    created = datetime.fromisoformat(d["created_at"])
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    offset = _PRIORITY_DEADLINE.get(d["priority"], timedelta(days=7))
    d["due_date"] = (created + offset).isoformat()
    return d
