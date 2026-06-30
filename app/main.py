from contextlib import asynccontextmanager
from datetime import UTC, datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from app import classifier, db
from app.models import TicketCreate, TicketResponse, TicketUpdate

load_dotenv()

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="TriageBot", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_FALLBACK = {"category": "question", "priority": "P3", "tags": []}


@app.post("/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(payload: TicketCreate):
    try:
        classification = classifier.classify_ticket(payload.title, payload.description)
    except Exception:
        classification = _FALLBACK

    ticket = db.create_ticket(
        title=payload.title,
        description=payload.description,
        category=classification["category"],
        priority=classification["priority"],
        tags=classification["tags"],
    )
    return ticket


@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    overdue: bool = False,
):
    return db.list_tickets(category=category, priority=priority, status=status, overdue=overdue)


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, payload: TicketUpdate):
    ticket = db.update_ticket(ticket_id, status=payload.status, priority=payload.priority)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get("/partials/tickets")
def tickets_partial(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    overdue: bool = False,
):
    tickets = db.list_tickets(
        category=category or None,
        priority=priority or None,
        status=status or None,
        overdue=overdue,
    )
    now = datetime.now(UTC).isoformat()
    return templates.TemplateResponse(
        "partials/tickets.html",
        {"request": request, "tickets": tickets, "now": now},
    )


@app.get("/")
def index(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    overdue: bool = False,
):
    tickets = db.list_tickets(
        category=category or None,
        priority=priority or None,
        status=status or None,
        overdue=overdue,
    )
    now = datetime.now(UTC).isoformat()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tickets": tickets,
            "now": now,
            "filters": {"category": category, "priority": priority, "status": status, "overdue": overdue},
        },
    )
