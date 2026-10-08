import pytest
from miniservice.api import TicketAPI
from miniservice.errors import Conflict, InvalidRequest
from miniservice.models import Ticket
from miniservice.repository import TicketRepository
from miniservice.service import TicketService
from miniservice.validation import normalize_title, validate_page

def test_title_trims_outer_whitespace(): assert normalize_title("  hello  ") == "hello"
def test_blank_title_is_rejected():
    with pytest.raises(InvalidRequest): normalize_title("  ")
def test_pagination_accepts_integer_strings(): assert validate_page("2", "10") == (2, 10)
def test_repository_get_returns_none_for_missing_record(): assert TicketRepository().get(5) is None
def test_ticket_order_is_stable_by_identifier():
    repo = TicketRepository(); repo.add(Ticket(9, "b")); repo.add(Ticket(2, "a"))
    assert [ticket.ticket_id for ticket in repo.list()] == [2, 9]
def test_duplicate_creation_is_rejected():
    service = TicketService(TicketRepository()); service.create(1, "one")
    with pytest.raises(Conflict): service.create(1, "again")
def test_page_reports_total_and_requested_page():
    service = TicketService(TicketRepository()); service.create(1, "one")
    result = service.page(1, 1)
    assert result["total"] == 1 and result["page"] == 1 and len(result["items"]) == 1
def test_api_returns_not_found_for_absent_ticket():
    api = TicketAPI(TicketService(TicketRepository()))
    assert api.get(99)[0] == 404
def test_create_api_returns_validation_error():
    api = TicketAPI(TicketService(TicketRepository()))
    assert api.create(1, " ")[0] == 400
def test_repository_keeps_created_event():
    repo = TicketRepository(); repo.add(Ticket(3, "x"))
    assert [event.kind for event in repo.events(3)] == ["created"]
