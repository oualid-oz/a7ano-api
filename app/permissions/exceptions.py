from app.core.exceptions import (
    AuthorizationException,
    ConflictException,
    ResourceNotFoundException,
)


class PermissionDeniedException(AuthorizationException):
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class RoleNotFoundException(ResourceNotFoundException):
    code = "ROLE_NOT_FOUND"
    message = "Role not found."


class PermissionNotFoundException(ResourceNotFoundException):
    code = "PERMISSION_NOT_FOUND"
    message = "Permission not found."


class RoleAlreadyAssignedException(ConflictException):
    code = "ROLE_ALREADY_ASSIGNED"
    message = "Role is already assigned to this user in the given scope."


class ProtectedSystemRoleException(ConflictException):
    code = "PROTECTED_SYSTEM_ROLE"
    message = "System roles cannot be deleted."
