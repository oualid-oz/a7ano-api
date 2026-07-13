from starlette.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from app.core.exceptions import AppException, AuthorizationException, ResourceNotFoundException


class ConversationNotFoundException(ResourceNotFoundException):
    code = "CONVERSATION_NOT_FOUND"
    message = "Conversation not found."


class MessageNotFoundException(ResourceNotFoundException):
    code = "MESSAGE_NOT_FOUND"
    message = "Message not found."


class ConversationAccessDeniedException(AuthorizationException):
    code = "CONVERSATION_ACCESS_DENIED"
    message = "You are not a participant of this conversation."


class DuplicateDirectConversationException(AppException):
    status_code = HTTP_409_CONFLICT
    code = "DUPLICATE_DIRECT_CONVERSATION"
    message = "A direct conversation between these members already exists."


class InvalidParticipantException(AppException):
    status_code = HTTP_400_BAD_REQUEST
    code = "INVALID_PARTICIPANT"
    message = "Invalid participant: exactly one of member_id or team_id must be provided."


class NotConversationAdminException(AuthorizationException):
    code = "NOT_CONVERSATION_ADMIN"
    message = "Only conversation admins can perform this action."


class CannotLeaveDirectConversationException(AppException):
    status_code = HTTP_400_BAD_REQUEST
    code = "CANNOT_LEAVE_DIRECT"
    message = "You cannot leave a direct conversation."
