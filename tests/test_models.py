import pytest
from pydantic import ValidationError

from app.models import TicketCreate, TicketUpdate

# ---------------------------------------------------------------------------
# TicketCreate — título
# ---------------------------------------------------------------------------


def test_title_valid():
    t = TicketCreate(title="Bug en login", description="No puedo entrar")
    assert t.title == "Bug en login"


def test_title_stripped():
    t = TicketCreate(title="  Bug  ", description="desc")
    assert t.title == "Bug"


def test_title_empty_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="", description="desc")


def test_title_only_spaces_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="   ", description="desc")


def test_title_exactly_200_chars_passes():
    TicketCreate(title="x" * 200, description="desc")


def test_title_201_chars_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="x" * 201, description="desc")


def test_title_1_char_passes():
    t = TicketCreate(title="x", description="desc")
    assert t.title == "x"


# ---------------------------------------------------------------------------
# TicketCreate — descripción
# ---------------------------------------------------------------------------


def test_description_valid():
    t = TicketCreate(title="titulo", description="Descripción correcta")
    assert t.description == "Descripción correcta"


def test_description_stripped():
    t = TicketCreate(title="titulo", description="  texto  ")
    assert t.description == "texto"


def test_description_empty_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="titulo", description="")


def test_description_only_spaces_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="titulo", description="   ")


def test_description_exactly_5000_chars_passes():
    TicketCreate(title="titulo", description="x" * 5000)


def test_description_5001_chars_raises():
    with pytest.raises(ValidationError):
        TicketCreate(title="titulo", description="x" * 5001)


# ---------------------------------------------------------------------------
# TicketUpdate — status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["open", "in_progress", "closed"])
def test_update_all_valid_statuses(status):
    u = TicketUpdate(status=status)
    assert u.status == status


def test_update_status_none_is_valid():
    u = TicketUpdate(status=None)
    assert u.status is None


def test_update_invalid_status_raises():
    with pytest.raises(ValidationError):
        TicketUpdate(status="eliminado")


def test_update_empty_object_is_valid():
    u = TicketUpdate()
    assert u.status is None
    assert u.priority is None


# ---------------------------------------------------------------------------
# TicketUpdate — priority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("priority", ["P1", "P2", "P3"])
def test_update_all_valid_priorities(priority):
    u = TicketUpdate(priority=priority)
    assert u.priority == priority


def test_update_priority_none_is_valid():
    u = TicketUpdate(priority=None)
    assert u.priority is None


def test_update_invalid_priority_raises():
    with pytest.raises(ValidationError):
        TicketUpdate(priority="P9")


def test_update_both_fields_valid():
    u = TicketUpdate(status="closed", priority="P2")
    assert u.status == "closed"
    assert u.priority == "P2"
