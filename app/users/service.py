from uuid import UUID

from app.core.security import hash_password, verify_password
from app.users.exceptions import (
    EmailAlreadyExistsException,
    InvalidPasswordException,
    UserNotFoundException,
)
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def create(self, data: UserCreate) -> User:
        existing = await self._repository.get_by_email(data.email)
        if existing is not None:
            raise EmailAlreadyExistsException()
        user = User(
            email=str(data.email),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        return await self._repository.create(user)

    async def get_by_id(self, user_id: UUID) -> User:
        user = await self._repository.get_or_404(user_id)
        return user

    async def get_by_email(self, email: str) -> User:
        user = await self._repository.get_by_email(email)
        if user is None:
            raise UserNotFoundException()
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        return await self._repository.update(user, update_data)

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise InvalidPasswordException()
        return await self._repository.update(user, {"password_hash": hash_password(new_password)})

    async def verify_email(self, user: User) -> User:
        if not user.is_verified:
            return await self._repository.update(user, {"is_verified": True})
        return user
