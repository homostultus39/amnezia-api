from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from src.api.v1.management.exceptions.auth import InvalidApiKeyException
from src.management.security import get_api_key_storage

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_api_key(
    request: Request,
    api_key: str | None = Depends(api_key_header),
) -> str:
    if not api_key:
        raise InvalidApiKeyException()
    
    if not get_api_key_storage().verify_api_key(api_key):
        raise InvalidApiKeyException()

    return api_key
