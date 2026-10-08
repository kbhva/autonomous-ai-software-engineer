"""Framework-free REST-style façade returning status and JSON-like data."""
from .errors import Conflict, InvalidRequest, NotFound

class TicketAPI:
    def __init__(self, service): self.service = service
    def create(self, ticket_id, title, tags=()):
        try: return 201, self.service.create(ticket_id, title, tags).__dict__
        except (Conflict, InvalidRequest) as exc: return 400, {"error": str(exc)}
    def get(self, ticket_id):
        ticket = self.service.repository.get(ticket_id)
        return (200, ticket.__dict__) if ticket else (404, {"error": "not found"})
    def list(self, page=1, size=20):
        try: return 200, self.service.page(page, size)
        except (ValueError, InvalidRequest) as exc: return 400, {"error": str(exc)}
