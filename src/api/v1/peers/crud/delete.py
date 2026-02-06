from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.peers.logger import logger
from src.api.v1.peers.schemas import DeletePeerResponse
from src.database.connection import SessionDep
from src.services.amnezia_service import AmneziaService

router = APIRouter()
amnezia_service = AmneziaService()


@router.delete("/{peer_id}", response_model=DeletePeerResponse)
async def delete_peer(
    peer_id: UUID,
    session: SessionDep,
) -> DeletePeerResponse:
    """
    Delete a peer and remove it from WireGuard configuration.
    """
    try:
        deleted = await amnezia_service.delete_client(session, peer_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Peer {peer_id} not found",
            )

        logger.info(f"Peer {peer_id} deleted successfully")
        return DeletePeerResponse(status="deleted")

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
            detail=f"Failed to delete peer: {str(exc)}",
        )
