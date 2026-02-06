from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.logger import logger
from src.api.v1.clients.schemas import CreateClientRequest, CreateClientResponse
from src.api.v1.deps.exceptions.clients import (
    config_generation_failed,
    ip_allocation_failed,
    protocol_not_supported,
    storage_error,
)
from src.database.connection import SessionDep
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()


@router.post("/", response_model=CreateClientResponse)
async def create_client(
    session: SessionDep,
    payload: CreateClientRequest,
) -> CreateClientResponse:
    """
    Create a new client and generate configurations for both app types.
    Configurations are stored in MinIO and returned with presigned URLs.
    """
    try:
        result = await clients_service.create_client(
            session=session,
            username=payload.username,
            protocol=payload.protocol,
            expires_at=payload.expires_at,
        )
        logger.info(f"Client {payload.username} created successfully with both configs")
        return CreateClientResponse(**result)
    except ValueError as exc:
        error_msg = str(exc).lower()
        logger.error(f"Validation error during client creation for {payload.username}: {error_msg}")
        if "protocol" in error_msg:
            raise protocol_not_supported(payload.protocol)
        if "ip" in error_msg:
            raise ip_allocation_failed(str(exc))
        raise config_generation_failed(str(exc))
    except SQLAlchemyError as exc:
        logger.error(f"Database error during client creation for {payload.username}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        logger.error(f"Unexpected error during client creation for {payload.username}: {error_msg}")
        if "minio" in error_msg or "storage" in error_msg:
            raise storage_error("upload", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client: {str(exc)}",
        )


