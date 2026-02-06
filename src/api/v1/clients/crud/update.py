from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.logger import logger
from src.api.v1.clients.schemas import UpdateClientRequest, UpdateClientResponse
from src.database.connection import SessionDep
from src.database.management.operations.client import get_client_by_id

router = APIRouter()


@router.patch("/{client_id}", response_model=UpdateClientResponse)
async def update_client(
    session: SessionDep,
    client_id: UUID,
    payload: UpdateClientRequest,
) -> UpdateClientResponse:
    """
    Update client metadata such as expiration time.
    """
    try:
        client = await get_client_by_id(session, client_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )

    if not client:
        logger.error(f"Client {client_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    try:
        if payload.expires_at is not None:
            client.expires_at = payload.expires_at

        await session.commit()
        logger.info(f"Client {client_id} updated successfully")
        return UpdateClientResponse(status="updated")
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.error(f"Database error during client {client_id} update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during client {client_id} update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update client: {str(exc)}",
        )


