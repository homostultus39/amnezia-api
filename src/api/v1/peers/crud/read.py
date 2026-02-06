from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import PeerResponse
from src.database.connection import SessionDep
from src.database.models import PeerModel, ProtocolModel, ClientModel
from src.minio.client import MinioClient
from src.services.amnezia_service import AmneziaService

router = APIRouter()
minio_client = MinioClient()
amnezia_service = AmneziaService()


@router.get("/", response_model=list[PeerResponse])
async def get_peers(
    session: SessionDep,
    protocol: str | None = Query(default="amneziawg"),
    online: bool | None = Query(default=None),
) -> list[PeerResponse]:
    """
    Retrieve all peers with optional filters.
    """
    try:
        result = await session.execute(
            select(ProtocolModel).where(ProtocolModel.name == protocol)
        )
        protocol_model = result.scalar_one_or_none()

        if not protocol_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Protocol {protocol} not found",
            )

        query = select(PeerModel).where(PeerModel.protocol_id == protocol_model.id)
        result = await session.execute(query)
        peers = result.scalars().all()

        wg_dump = await amnezia_service.connection.get_wg_dump()
        peers_data = amnezia_service._parse_wg_dump(wg_dump)

        peer_responses = []
        for peer in peers:
            wg_peer = peers_data.get(peer.public_key, {})
            is_online = wg_peer.get("online", False)

            if online is not None and is_online != online:
                continue

            object_name = f"configs/{protocol}/{peer.client_id}/{peer.app_type}"
            try:
                config_url = await minio_client.presigned_get_url(object_name)
            except Exception:
                config_url = None

            peer_responses.append(
                PeerResponse(
                    id=str(peer.id),
                    client_id=str(peer.client_id),
                    username=peer.client.username,
                    app_type=peer.app_type,
                    protocol=protocol,
                    endpoint=wg_peer.get("endpoint") or peer.endpoint,
                    public_key=peer.public_key,
                    online=is_online,
                    last_handshake=wg_peer.get("last_handshake"),
                    url=config_url or "",
                )
            )

        logger.info(f"Retrieved {len(peer_responses)} peers")
        return peer_responses

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(f"Database error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve peers: {str(exc)}",
        )


@router.get("/client/{client_id}", response_model=list[PeerResponse])
async def get_client_peers(
    client_id: UUID,
    session: SessionDep,
    protocol: str = Query(default="amneziawg"),
) -> list[PeerResponse]:
    """
    Retrieve all peers for a specific client.
    """
    try:
        result = await session.execute(
            select(ClientModel).where(ClientModel.id == client_id)
        )
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found",
            )

        wg_dump = await amnezia_service.connection.get_wg_dump()
        peers_data = amnezia_service._parse_wg_dump(wg_dump)

        peer_responses = []
        for peer in client.peers:
            wg_peer = peers_data.get(peer.public_key, {})

            object_name = f"configs/{protocol}/{peer.client_id}/{peer.app_type}"
            try:
                config_url = await minio_client.presigned_get_url(object_name)
            except Exception:
                config_url = None

            peer_responses.append(
                PeerResponse(
                    id=str(peer.id),
                    client_id=str(client.id),
                    username=client.username,
                    app_type=peer.app_type,
                    protocol=protocol,
                    endpoint=wg_peer.get("endpoint") or peer.endpoint,
                    public_key=peer.public_key,
                    online=wg_peer.get("online", False),
                    last_handshake=wg_peer.get("last_handshake"),
                    url=config_url or "",
                )
            )

        logger.info(f"Retrieved {len(peer_responses)} peers for client {client_id}")
        return peer_responses

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(f"Database error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client peers: {str(exc)}",
        )
