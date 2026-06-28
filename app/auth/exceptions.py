from app.core.exceptions import (
    AuthenticationException,
    BadRequestException,
    ConflictException,
)


class InvalidCredentialsException(AuthenticationException):
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password."


class AccountLockedException(AuthenticationException):
    code = "ACCOUNT_LOCKED"
    message = "Account is temporarily locked due to too many failed login attempts."


class InvalidOrExpiredTokenException(AuthenticationException):
    code = "INVALID_OR_EXPIRED_TOKEN"
    message = "Token is invalid or expired."


class SessionExpiredException(AuthenticationException):
    code = "SESSION_EXPIRED"
    message = "Session has expired or been revoked."


class EmailAlreadyVerifiedException(ConflictException):
    code = "EMAIL_ALREADY_VERIFIED"
    message = "Email address is already verified."


class EmailVerificationTokenInvalidException(BadRequestException):
    code = "INVALID_EMAIL_VERIFICATION_TOKEN"
    message = "Email verification token is invalid or expired."


class PasswordResetTokenInvalidException(BadRequestException):
    code = "INVALID_PASSWORD_RESET_TOKEN"
    message = "Password reset token is invalid or expired."
