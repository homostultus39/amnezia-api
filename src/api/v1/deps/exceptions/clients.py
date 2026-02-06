from fastapi import HTTPException, status


def peer_not_found(peer_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Peer with ID '{peer_id}' not found",
    )


def protocol_not_supported(protocol: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Protocol '{protocol}' is not supported",
    )


def config_generation_failed(reason: str = "Unknown error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to generate configuration: {reason}",
    )


def ip_allocation_failed(reason: str = "No available IP addresses") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to allocate IP address: {reason}",
    )


def storage_error(operation: str, reason: str = "Unknown error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Storage operation '{operation}' failed: {reason}",
    )
