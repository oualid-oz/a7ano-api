from app.core.exceptions import ResourceNotFoundException


class EventNotFoundException(ResourceNotFoundException):
    code = "EVENT_NOT_FOUND"
    message = "Event not found."
