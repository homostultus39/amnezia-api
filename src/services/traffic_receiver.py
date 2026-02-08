from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.services.management.amnezia_connection import AmneziaConnection
from src.management.logger import configure_logger

logger = configure_logger("TrafficReceiver", "purple")


@dataclass
class PeerTrafficData:
    public_key: str
    endpoint: Optional[str]
    allowed_ips: list[str]
    last_handshake: Optional[datetime]
    rx_bytes: int
    tx_bytes: int
    online: bool
    persistent_keepalive: int


class TrafficReceiver:
    def __init__(self, container_name: Optional[str] = None):
        self.connection = AmneziaConnection(container_name)

    async def get_peer_traffic(self, public_key: str) -> Optional[PeerTrafficData]:
        all_peers = await self.get_all_peers_traffic()
        return all_peers.get(public_key)

    async def get_all_peers_traffic(self) -> dict[str, PeerTrafficData]:
        dump_output = await self.connection.get_wg_dump()
        return self._parse_wg_dump(dump_output)

    def _parse_wg_dump(self, dump_output: str) -> dict[str, PeerTrafficData]:
        peers = {}
        lines = dump_output.strip().split("\n")

        if not lines:
            logger.warning("Empty dump output received")
            return peers

        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 8:
                logger.debug(f"Skipping malformed line: {line}")
                continue

            public_key = parts[0]
            endpoint = parts[2] if parts[2] != "(none)" else None
            allowed_ips_str = parts[3]
            last_handshake_ts = int(parts[4]) if parts[4] != "0" else None
            rx_bytes = int(parts[5])
            tx_bytes = int(parts[6])
            persistent_keepalive = int(parts[7]) if parts[7] != "off" else 0

            last_handshake = None
            if last_handshake_ts:
                last_handshake = datetime.fromtimestamp(last_handshake_ts)

            online = False
            if last_handshake:
                time_diff = (datetime.now() - last_handshake).total_seconds()
                from src.management.settings import get_settings
                settings = get_settings()
                online = time_diff < settings.peer_online_threshold_seconds

            allowed_ips = [ip.strip() for ip in allowed_ips_str.split(",") if ip.strip()]

            peers[public_key] = PeerTrafficData(
                public_key=public_key,
                endpoint=endpoint,
                allowed_ips=allowed_ips,
                last_handshake=last_handshake,
                rx_bytes=rx_bytes,
                tx_bytes=tx_bytes,
                online=online,
                persistent_keepalive=persistent_keepalive,
            )

        logger.debug(f"Parsed traffic data for {len(peers)} peers")
        return peers

    async def get_total_traffic(self) -> dict[str, int]:
        all_peers = await self.get_all_peers_traffic()

        total_rx = sum(peer.rx_bytes for peer in all_peers.values())
        total_tx = sum(peer.tx_bytes for peer in all_peers.values())

        logger.debug(f"Total traffic: RX={total_rx} bytes, TX={total_tx} bytes")

        return {
            "total_rx_bytes": total_rx,
            "total_tx_bytes": total_tx,
            "total_peers": len(all_peers),
            "online_peers": sum(1 for peer in all_peers.values() if peer.online),
        }

    async def get_peers_by_status(self, online_only: bool = True) -> dict[str, PeerTrafficData]:
        all_peers = await self.get_all_peers_traffic()

        if online_only:
            filtered = {k: v for k, v in all_peers.items() if v.online}
            logger.debug(f"Filtered {len(filtered)} online peers from {len(all_peers)} total")
            return filtered

        offline = {k: v for k, v in all_peers.items() if not v.online}
        logger.debug(f"Filtered {len(offline)} offline peers from {len(all_peers)} total")
        return offline
