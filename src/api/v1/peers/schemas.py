from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from src.database.models import AppType


class CreatePeerRequest(BaseModel):
    client_id: Optional[UUID] = None
    username: Optional[str] = None
    app_type: AppType
    protocol: str = "amneziawg"


class PeerResponse(BaseModel):
    id: str
    client_id: str
    username: str
    app_type: str
    protocol: str
    endpoint: str
    public_key: str
    online: bool
    last_handshake: Optional[datetime]
    url: str


class UpdatePeerRequest(BaseModel):
    app_type: Optional[AppType] = None
    protocol: Optional[str] = None


class DeletePeerResponse(BaseModel):
    status: str
