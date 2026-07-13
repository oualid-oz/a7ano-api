from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dms.repository import ConversationRepository, MessageRepository, ParticipantRepository
from app.dms.service import DMService


def get_conversation_repository(
    session: AsyncSession = Depends(get_db),
) -> ConversationRepository:
    return ConversationRepository(session)


def get_participant_repository(
    session: AsyncSession = Depends(get_db),
) -> ParticipantRepository:
    return ParticipantRepository(session)


def get_message_repository(
    session: AsyncSession = Depends(get_db),
) -> MessageRepository:
    return MessageRepository(session)


def get_dm_service(
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    part_repo: ParticipantRepository = Depends(get_participant_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
) -> DMService:
    return DMService(conv_repo, part_repo, msg_repo)
