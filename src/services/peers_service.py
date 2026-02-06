from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.amnezia_service import AmneziaService
from src.database.models import ClientModel, PeerModel
from src.management.logger import configure_logger

logger = configure_logger("PeersService", "cyan")


class PeersService:
    def __init__(self):
        self._services = {
            "amneziawg": AmneziaService(),
        }

    def _get_service(self, protocol: str):
        service = self._services.get(protocol.lower())
        if not service:
            logger.error(f"Unsupported protocol: {protocol}")
            raise ValueError(f"Unsupported protocol: {protocol}")
        return service

    async def resolve_client(
        self,
        session: AsyncSession,
        client_id: Optional[UUID] = None,
        username: Optional[str] = None,
    ) -> ClientModel:
        if not client_id and not username:
            raise ValueError("Either client_id or username must be provided")

        if client_id:
            result = await session.execute(
                select(ClientModel).where(ClientModel.id == client_id)
            )
        else:
            result = await session.execute(
                select(ClientModel).where(ClientModel.username == username)
            )

        client = result.scalar_one_or_none()
        if not client:
            identifier = client_id or username
            raise ValueError(f"Client {identifier} not found")

        return client

    async def get_peer_by_id(self, session: AsyncSession, peer_id: UUID) -> Optional[PeerModel]:
        result = await session.execute(
            select(PeerModel).where(PeerModel.id == peer_id)
        )
        return result.scalar_one_or_none()
