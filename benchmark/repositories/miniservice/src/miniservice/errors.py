"""Domain exceptions exposed by the service layer."""
class ServiceError(Exception):
    """Base error for expected business-rule failures."""
class NotFound(ServiceError): pass
class Conflict(ServiceError): pass
class InvalidRequest(ServiceError): pass
