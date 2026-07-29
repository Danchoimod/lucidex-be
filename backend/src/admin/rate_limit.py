import hashlib
import hmac
import ipaddress
import logging
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import settings

logger = logging.getLogger("lucidex.admin.rate_limit")

_INCREMENT_WITH_TTL = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
local ttl = redis.call("TTL", KEYS[1])
return {count, ttl}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int
    remaining: int


def normalize_ip(ip_address: str) -> str:
    value = ip_address.strip()
    try:
        return ipaddress.ip_address(value).compressed.lower()
    except ValueError:
        return value.lower() or "unknown"


def hash_ip(ip_address: str) -> str:
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        normalize_ip(ip_address).encode(),
        hashlib.sha256,
    ).hexdigest()


def build_admin_login_rate_limit_key(ip_hash: str) -> str:
    return f"rate-limit:v1:lucidex:{settings.ENV}:admin-login:ip:{ip_hash}"


class AdminLoginRateLimiter:
    def __init__(self) -> None:
        self._redis: Redis | None = None

    def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        return self._redis

    async def consume(self, ip_address: str) -> RateLimitResult:
        key = build_admin_login_rate_limit_key(hash_ip(ip_address))
        try:
            result = await self._client().eval(
                _INCREMENT_WITH_TTL,
                1,
                key,
                settings.ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            )
        except RedisError as exc:
            logger.warning(
                "admin_login_rate_limit_unavailable",
                extra={
                    "behavior": "fail_open",
                    "failure_reason": type(exc).__name__,
                },
            )
            return RateLimitResult(
                allowed=True,
                retry_after=0,
                remaining=settings.ADMIN_LOGIN_RATE_LIMIT_REQUESTS,
            )

        count, ttl = int(result[0]), int(result[1])
        retry_after = (
            ttl
            if ttl > 0
            else settings.ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS
        )
        return RateLimitResult(
            allowed=count <= settings.ADMIN_LOGIN_RATE_LIMIT_REQUESTS,
            retry_after=max(retry_after, 1),
            remaining=max(
                settings.ADMIN_LOGIN_RATE_LIMIT_REQUESTS - count,
                0,
            ),
        )

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


admin_login_rate_limiter = AdminLoginRateLimiter()
