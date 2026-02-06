from typing import Any

from src.database.models import ClientModel
from src.services.utils.config_storage import get_config_object_name
from src.minio.client import MinioClient


async def format_client_with_peers(
    client: ClientModel,
    protocol: str,
    peers_data: dict[str, dict[str, Any]],
    minio_client: MinioClient
) -> dict:
    peers_dict: dict[str, dict[str, Any]] = {}

    for peer in client.peers:
        wg_peer = peers_data.get(peer.public_key, {})
        object_name = get_config_object_name(protocol, client.id, peer.app_type)
        try:
            url = await minio_client.presigned_get_url(object_name)
        except Exception:
            url = None

        peers_dict[peer.app_type] = {
            "id": str(peer.id),
            "endpoint": wg_peer.get("endpoint") or peer.endpoint,
            "protocol": protocol,
            "url": url,
            "online": wg_peer.get("online", False),
            "last_handshake": wg_peer.get("last_handshake"),
        }

    return {
        "id": str(client.id),
        "username": client.username,
        "expires_at": client.expires_at,
        "peers": peers_dict,
    }

