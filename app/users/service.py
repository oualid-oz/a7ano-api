from uuid import UUID

from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.users.exceptions import (
    EmailAlreadyExistsException,
    InvalidPasswordException,
    UserNotFoundException,
)
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def create(self, data: UserCreate) -> User:
        logger.info("Creating user", extra={"email": str(data.email)})
        existing = await self._repository.get_by_email(data.email)
        if existing is not None:
            logger.warning(
                "User creation failed: email already exists", extra={"email": str(data.email)}
            )
            raise EmailAlreadyExistsException()
        user = User(
            email=str(data.email),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        user = await self._repository.create(user)
        logger.info("User created", extra={"user_id": str(user.id), "email": str(user.email)})
        return user

    async def get_by_id(self, user_id: UUID) -> User:
        logger.info("Fetching user by id", extra={"user_id": str(user_id)})
        user = await self._repository.get_or_404(user_id)
        logger.info("User fetched", extra={"user_id": str(user.id), "email": str(user.email)})
        return user

    async def get_by_email(self, email: str) -> User:
        logger.info("Fetching user by email", extra={"email": str(email)})
        user = await self._repository.get_by_email(email)
        if user is None:
            logger.warning("User not found by email", extra={"email": str(email)})
            raise UserNotFoundException()
        logger.info("User fetched", extra={"user_id": str(user.id)})
        return user

    async def list_active(self, search: str | None = None) -> list[User]:
        logger.info("Listing active users", extra={"search": search})
        users = await self._repository.list_active(search)
        logger.info("Active users listed", extra={"count": len(users)})
        return users

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        logger.info("Updating user profile", extra={"user_id": str(user.id)})
        update_data = data.model_dump(exclude_unset=True)
        logger.info(
            "Updating profile fields",
            extra={"user_id": str(user.id), "fields": list(update_data.keys())},
        )
        updated = await self._repository.update(user, update_data)
        logger.info("User profile updated", extra={"user_id": str(updated.id)})
        return updated

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        logger.info("Password change requested", extra={"user_id": str(user.id)})
        if not verify_password(current_password, user.password_hash):
            logger.warning(
                "Password change failed: invalid current password", extra={"user_id": str(user.id)}
            )
            raise InvalidPasswordException()
        updated = await self._repository.update(
            user, {"password_hash": hash_password(new_password)}
        )
        logger.info("Password changed successfully", extra={"user_id": str(user.id)})
        return updated

    async def verify_email(self, user: User) -> User:
        logger.info(
            "Email verification",
            extra={"user_id": str(user.id), "already_verified": user.is_verified},
        )
        if not user.is_verified:
            updated = await self._repository.update(user, {"is_verified": True})
            logger.info("Email verified", extra={"user_id": str(user.id)})
            return updated
        logger.info("Email already verified, skipped", extra={"user_id": str(user.id)})
        return user
