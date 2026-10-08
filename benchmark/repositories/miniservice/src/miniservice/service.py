"""Business operations for ticket lifecycle and listing."""
from dataclasses import replace
from .errors import Conflict, NotFound
from .models import Ticket
from .validation import normalize_title, validate_page

class TicketService:
    _TRANSITIONS = {"open": {"in_progress", "closed"}, "in_progress": {"open", "closed"}, "closed": set()}
    def __init__(self, repository): self.repository = repository
    def create(self, ticket_id, title, tags=()):
        if self.repository.get(ticket_id) is not None: raise Conflict("duplicate ticket")
        ticket = Ticket(ticket_id, normalize_title(title), tags=tuple(tags))
        self.repository.add(ticket); return ticket
    def transition(self, ticket_id, status):
        ticket = self.repository.get(ticket_id)
        if ticket is None: raise NotFound(ticket_id)
        updated = replace(ticket, status=status)
        self.repository.replace(updated); return updated
    def page(self, page=1, size=20):
        page, size = validate_page(page, size)
        items = self.repository.list(); start = (page - 1) * size
        return {"items": items[start:start + size], "total": len(items), "page": page, "size": size}
