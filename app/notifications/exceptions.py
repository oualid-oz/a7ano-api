from app.core.exceptions import ResourceNotFoundException


class NotificationNotFoundException(ResourceNotFoundException):
    code = "NOTIFICATION_NOT_FOUND"
    message = "Notification not found."
