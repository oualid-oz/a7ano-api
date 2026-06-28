from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ResourceNotFoundException,
)


class OrganizationNotFoundException(ResourceNotFoundException):
    code = "ORGANIZATION_NOT_FOUND"
    message = "Organization not found."


class OrganizationSlugExistsException(ConflictException):
    code = "ORGANIZATION_SLUG_EXISTS"
    message = "An organization with this slug already exists."


class InvitationNotFoundException(ResourceNotFoundException):
    code = "INVITATION_NOT_FOUND"
    message = "Invitation not found."


class InvitationExpiredException(BadRequestException):
    code = "INVITATION_EXPIRED"
    message = "Invitation has expired."


class InvitationAlreadyProcessedException(BadRequestException):
    code = "INVITATION_ALREADY_PROCESSED"
    message = "Invitation has already been accepted or revoked."
