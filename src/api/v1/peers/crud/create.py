from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import CreatePeerRequest, PeerResponse
from src.database.connection import SessionDep
from src.services.utils.config_storage import get_config_object_name
from src.minio.client import MinioClient
from src.services.peers_service import PeersService

router = APIRouter()
peers_service = PeersService()
minio_client = MinioClient()


@router.post("/", response_model=PeerResponse)
async def create_peer(
    session: SessionDep,
    payload: CreatePeerRequest,
) -> PeerResponse:
    """
    Create a new peer for an existing client.
    """
    try:
        client = await peers_service.resolve_client(
            session=session,
            client_id=payload.client_id,
            username=payload.username,
        )

        service = peers_service._get_service(payload.protocol)

        peer_data = await service.create_peer(
            session=session,
            client=client,
            app_type=payload.app_type.value,
        )

        peer = peer_data["peer"]
        wg_dump = await service.connection.get_wg_dump()
        peers_data = service._parse_wg_dump(wg_dump)

        await session.commit()

        object_name = get_config_object_name(payload.protocol, client.id, payload.app_type.value)
        config_url = await minio_client.presigned_get_url(object_name)

        wg_peer = peers_data.get(peer.public_key, {})

        logger.info(f"Peer created for client {client.username}: {payload.app_type.value}")

        return PeerResponse(
            id=str(peer.id),
            client_id=str(client.id),
            username=client.username,
            app_type=payload.app_type.value,
            protocol=payload.protocol,
            endpoint=wg_peer.get("endpoint") or peer.endpoint,
            public_key=peer.public_key,
            online=wg_peer.get("online", False),
            last_handshake=wg_peer.get("last_handshake"),
            url=config_url,
        )

    except ValueError as exc:
        logger.error(f"Validation error during peer creation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except IntegrityError as exc:
        logger.error(f"Integrity error: {exc}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Peer with this app_type already exists for this client",
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error: {exc}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during peer creation: {exc}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create peer: {str(exc)}",
        )
