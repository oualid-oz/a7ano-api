from app.core.exceptions import (
    AuthenticationException,
    BadRequestException,
    ConflictException,
    ResourceNotFoundException,
)


class UserNotFoundException(ResourceNotFoundException):
    message = "User not found."


class EmailAlreadyExistsException(ConflictException):
    code = "EMAIL_ALREADY_EXISTS"
    message = "A user with this email already exists."


class InvalidPasswordException(AuthenticationException):
    code = "INVALID_PASSWORD"
    message = "Current password is incorrect."


class UserNotVerifiedException(BadRequestException):
    code = "USER_NOT_VERIFIED"
    message = "Email address has not been verified."
