"""Request normalization shared by API and service callers."""
from .errors import InvalidRequest

def normalize_title(title):
    """Normalize a user-supplied title and reject blank input."""
    if not isinstance(title, str) or not title.strip():
        raise InvalidRequest("title is required")
    return title.strip()

def validate_page(page, size):
    page, size = int(page), int(size)
    if page < 1 or not 1 <= size <= 100:
        raise InvalidRequest("invalid pagination")
    return page, size
