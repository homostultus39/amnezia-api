from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.clients.logger import logger
from src.api.v1.clients.schemas import ClientResponse
from src.api.v1.deps.exceptions.clients import protocol_not_supported
from src.database.connection import SessionDep
from src.database.models import ClientModel
from src.minio.client import MinioClient
from src.services.clients_service import ClientsService

router = APIRouter()
clients_service = ClientsService()
minio_client = MinioClient()


async def _add_config_urls(client: dict, protocol: str) -> None:
    client_id = client.get("id")
    if not client_id:
        return

    for app_type, peer_info in client.get("peers", {}).items():
        object_name = f"configs/{protocol}/{client_id}/{app_type}"
        try:
            peer_info["url"] = await minio_client.presigned_get_url(object_name)
        except Exception as exc:
            logger.warning(f"Failed to generate presigned URL for {app_type} peer of client {client_id}: {exc}")
            peer_info["url"] = None


@router.get("/", response_model=list[ClientResponse])
async def get_clients(
    session: SessionDep,
    protocol: str | None = Query(default=None, min_length=1, max_length=100),
    expires_before: datetime | None = Query(default=None),
    expires_after: datetime | None = Query(default=None),
) -> list[ClientResponse]:
    """
    Retrieve all clients with optional filters.
    """
    try:
        clients = await clients_service.get_clients(session, protocol)

        if expires_before or expires_after:
            filtered_clients = []
            for client in clients:
                expires_at = client.get("expires_at")
                if expires_before and expires_at >= expires_before:
                    continue
                if expires_after and expires_at <= expires_after:
                    continue
                filtered_clients.append(client)
            clients = filtered_clients

        for client in clients:
            await _add_config_urls(client, protocol or "amneziawg")

        logger.info(f"Retrieved {len(clients)} clients successfully")
        return [ClientResponse(**client) for client in clients]

    except HTTPException as exc:
        logger.error(f"HTTP error during clients retrieval: {exc.detail}")
        raise
    except ValueError as exc:
        logger.error(f"Value error during clients retrieval: {exc}")
        if protocol:
            raise protocol_not_supported(protocol)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters",
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error during clients retrieval: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during clients retrieval: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clients: {str(exc)}",
        )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    session: SessionDep,
    protocol: str = Query(default="amneziawg", min_length=1, max_length=100),
) -> ClientResponse:
    """
    Retrieve a single client by ID.
    """
    try:
        result = await session.execute(
            select(ClientModel).where(ClientModel.id == client_id)
        )
        client_model = result.scalar_one_or_none()

        if not client_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found",
            )

        clients = await clients_service.get_clients(session, protocol)
        client_dict = next((c for c in clients if c["id"] == str(client_id)), None)

        if not client_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found",
            )

        await _add_config_urls(client_dict, protocol)

        logger.info(f"Retrieved client {client_id} successfully")
        return ClientResponse(**client_dict)

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(f"Database error during client retrieval: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during client retrieval: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client: {str(exc)}",
        )


