"""In-memory repository with explicit deterministic ordering."""
from .models import Event, Ticket

class TicketRepository:
    def __init__(self):
        self._tickets = {}
        self._events = []
    def add(self, ticket):
        self._tickets[ticket.ticket_id] = ticket
        self._events.append(Event(ticket.ticket_id, "created", len(self._events) + 1))
    def get(self, ticket_id):
        return self._tickets.get(ticket_id)
    def replace(self, ticket):
        self._tickets[ticket.ticket_id] = ticket
        self._events.append(Event(ticket.ticket_id, ticket.status, len(self._events) + 1))
    def list(self):
        return [self._tickets[key] for key in sorted(self._tickets)]
    def events(self, ticket_id):
        return tuple(event for event in self._events if event.ticket_id == ticket_id)
