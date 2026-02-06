from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PeerConfigResponse(BaseModel):
    protocol: str
    config: str
    url: str


class CreateClientResponse(BaseModel):
    id: str
    amnezia_vpn: PeerConfigResponse
    amnezia_wg: PeerConfigResponse


class PeerInfoResponse(BaseModel):
    id: str
    endpoint: str
    protocol: str
    url: str
    online: bool
    last_handshake: Optional[datetime]


class ClientResponse(BaseModel):
    id: str
    username: str
    expires_at: datetime
    peers: dict[str, PeerInfoResponse]


class CreateClientRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    protocol: str = Field(default="amneziawg", min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class UpdateClientRequest(BaseModel):
    expires_at: Optional[datetime] = None


class DeleteClientResponse(BaseModel):
    status: str


class UpdateClientResponse(BaseModel):
    status: str
