from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.amnezia_service import AmneziaService
from src.database.models import ClientModel, PeerModel
from src.database.management.operations.client import get_client_by_id, get_client_by_username
from src.database.management.operations.peer import get_peer_by_id
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
            client = await get_client_by_id(session, client_id)
        else:
            client = await get_client_by_username(session, username)

        if not client:
            identifier = client_id or username
            raise ValueError(f"Client {identifier} not found")

        return client
