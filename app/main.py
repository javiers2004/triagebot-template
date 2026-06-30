from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import classifier, db
from app.models import TicketCreate, TicketResponse, TicketUpdate

_ALLOWED_STATUSES = {"open", "in_progress", "resolved", "closed"}
_ALLOWED_PRIORITIES = {"P1", "P2", "P3"}

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
):
    return db.list_tickets(category=category, priority=priority, status=status)


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, payload: TicketUpdate):
    ticket = db.update_ticket(
        ticket_id,
        status=payload.status,
        priority=payload.priority,
        assignees=payload.assignees,
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.get("/partials/tickets")
def tickets_partial(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
):
    tickets = db.list_tickets(category=category or None, priority=priority or None, status=status or None)
    return templates.TemplateResponse(
        "partials/tickets.html",
        {"request": request, "tickets": tickets},
    )


@app.get("/partials/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_row(request: Request, ticket_id: int):
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return templates.TemplateResponse("partials/ticket_row.html", {"request": request, "ticket": ticket})


@app.get("/partials/tickets/{ticket_id}/edit", response_class=HTMLResponse)
def ticket_edit_row(request: Request, ticket_id: int):
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return templates.TemplateResponse("partials/ticket_edit.html", {"request": request, "ticket": ticket})


@app.patch("/partials/tickets/{ticket_id}", response_class=HTMLResponse)
def patch_ticket_html(
    request: Request,
    ticket_id: int,
    status: str | None = Form(None),
    priority: str | None = Form(None),
    assignees: str | None = Form(None),
):
    valid_status = status if status in _ALLOWED_STATUSES else None
    valid_priority = priority if priority in _ALLOWED_PRIORITIES else None
    assignee_list = [a.strip() for a in assignees.split(",") if a.strip()] if assignees is not None else None
    ticket = db.update_ticket(ticket_id, status=valid_status, priority=valid_priority, assignees=assignee_list)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return templates.TemplateResponse("partials/ticket_row.html", {"request": request, "ticket": ticket})


@app.get("/")
def index(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
):
    tickets = db.list_tickets(category=category or None, priority=priority or None, status=status or None)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tickets": tickets,
            "filters": {"category": category, "priority": priority, "status": status},
        },
    )
