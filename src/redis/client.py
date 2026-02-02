import hashlib
from typing import Optional

from src.management.settings import get_settings
from src.redis.connection import get_redis_client

settings = get_settings()


class RedisClient:
    def __init__(self) -> None:
        self._client = get_redis_client()

    def _token_key(self, token: str, prefix: str) -> str:
        digest = hashlib.sha256(token.encode()).hexdigest()
        return f"{prefix}:{digest}"

    def _default_token_ex(self, token_type: str) -> int:
        if token_type == "access":
            return settings.jwt_access_token_expire_minutes * 60
        if token_type == "refresh":
            return settings.jwt_refresh_token_expire_minutes * 60
        raise ValueError(f"Unsupported token type: {token_type}")

    async def blacklist_token(self, token: str, ex: Optional[int] = None) -> None:
        ttl = ex if ex is not None else settings.jwt_blacklist_ex
        key = self._token_key(token, "jwt:blacklist")
        await self._client.set(key, "1", ex=ttl)

    async def is_token_blacklisted(self, token: str) -> bool:
        key = self._token_key(token, "jwt:blacklist")
        return await self._client.exists(key) == 1

    async def store_token(self, token: str, token_type: str, ex: Optional[int] = None) -> None:
        ttl = ex if ex is not None else self._default_token_ex(token_type)
        key = self._token_key(token, f"jwt:{token_type}")
        await self._client.set(key, "1", ex=ttl)

    async def is_token_active(self, token: str, token_type: str) -> bool:
        key = self._token_key(token, f"jwt:{token_type}")
        return await self._client.exists(key) == 1

    async def revoke_token(self, token: str, token_type: str) -> None:
        key = self._token_key(token, f"jwt:{token_type}")
        await self._client.delete(key)

