"""Read-only event summaries for operational diagnostics."""
def event_timeline(repository, ticket_id):
    """Return event kinds in append order for one ticket."""
    return [event.kind for event in repository.events(ticket_id)]

def event_sequences(repository, ticket_id):
    """Return sequence markers for a ticket's event history."""
    return [event.sequence for event in repository.events(ticket_id)]
