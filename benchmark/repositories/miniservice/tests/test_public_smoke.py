from miniservice.api import TicketAPI
from miniservice.repository import TicketRepository
from miniservice.service import TicketService

def test_public_service_flow():
    repo = TicketRepository(); service = TicketService(repo); api = TicketAPI(service)
    assert api.create(1, "A ticket")[0] == 201
    assert api.get(1)[0] == 200
    assert api.list()[1]["total"] == 1
    assert service.transition(1, "in_progress").status == "in_progress"
