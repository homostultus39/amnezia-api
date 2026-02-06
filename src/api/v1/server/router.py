from fastapi import APIRouter, HTTPException, status

from src.api.v1.server.logger import logger
from src.api.v1.server.schemas import (
    ServerStatusResponse,
    ServerTrafficResponse,
    RestartServerResponse,
)
from src.services.host_service import HostService
from src.services.traffic_receiver import TrafficReceiver
from src.management.settings import get_settings

router = APIRouter(prefix="/server", tags=["Server"])

settings = get_settings()
host_service = HostService()
traffic_receiver = TrafficReceiver(settings.amnezia_container_name)


@router.get("/status", response_model=ServerStatusResponse)
async def get_server_status() -> ServerStatusResponse:
    """
    Get the current status of the Amnezia server.
    """
    try:
        container_name = settings.amnezia_container_name
        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running")
            return ServerStatusResponse(
                status="stopped",
                container_name=container_name,
                port=None,
                interface="",
                protocol="amneziawg",
            )

        port = await host_service.get_container_port(container_name, "udp")

        logger.info(f"Server status retrieved: {container_name} is running on port {port}")

        return ServerStatusResponse(
            status="running",
            container_name=container_name,
            port=port,
            interface="wg0",
            protocol="amneziawg",
        )

    except Exception as exc:
        logger.error(f"Failed to get server status: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server status: {str(exc)}",
        )


@router.get("/traffic", response_model=ServerTrafficResponse)
async def get_server_traffic() -> ServerTrafficResponse:
    """
    Get total traffic statistics for the server.
    """
    try:
        traffic_data = await traffic_receiver.get_total_traffic()

        logger.info(
            f"Traffic retrieved: RX={traffic_data['total_rx_bytes']} "
            f"TX={traffic_data['total_tx_bytes']} "
            f"Peers={traffic_data['total_peers']} "
            f"Online={traffic_data['online_peers']}"
        )

        return ServerTrafficResponse(**traffic_data)

    except Exception as exc:
        logger.error(f"Failed to get server traffic: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server traffic: {str(exc)}",
        )


@router.post("/restart", response_model=RestartServerResponse)
async def restart_server() -> RestartServerResponse:
    """
    Restart the Amnezia server container.
    """
    try:
        container_name = settings.amnezia_container_name

        is_running = await host_service.is_container_running(container_name)

        if not is_running:
            logger.warning(f"Container {container_name} is not running, cannot restart")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container {container_name} is not running",
            )

        await host_service.run_command(f"docker restart {container_name}", timeout=10000)

        logger.info(f"Server {container_name} restarted successfully")

        return RestartServerResponse(
            status="restarted",
            message=f"Server {container_name} has been restarted successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to restart server: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart server: {str(exc)}",
        )
