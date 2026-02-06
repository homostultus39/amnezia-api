from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class BaseProtocolService(ABC):
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        pass

    @abstractmethod
    async def get_clients(self, session: AsyncSession) -> list[dict]:
        pass

    @abstractmethod
    async def create_peer(
        self,
        session: AsyncSession,
        client: "ClientModel",
        app_type: str,
    ) -> dict:
        pass

    @abstractmethod
    async def delete_client(self, session: AsyncSession, peer_id: UUID) -> bool:
        pass

    async def cleanup_expired_clients(self, session: AsyncSession) -> int:
        from sqlalchemy import select
        from src.database.models import ClientModel, PeerModel

        result = await session.execute(
            select(ClientModel).where(
                ClientModel.expires_at < datetime.now(),
                ClientModel.peers.any(PeerModel.protocol_id == await self._get_protocol_id(session))
            )
        )
        expired_clients = result.scalars().all()

        deleted_count = 0
        for client in expired_clients:
            for peer in client.peers:
                try:
                    await self.delete_client(session, peer.id)
                    deleted_count += 1
                except Exception:
                    pass

        return deleted_count

    @abstractmethod
    async def _get_protocol_id(self, session: AsyncSession) -> UUID:
        pass
