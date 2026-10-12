"""Small Redis counters against brute force (login, share passwords, registration)."""

import ipaddress

from fastapi import Request

from app.core.errors import AppError
from app.core.redis import redis_client


def client_ip(request: Request) -> str | None:
    """The browser's address.

    Requests arrive through nginx (and Cloudflare), so the peer is a proxy on a private network; only then
    are forwarding headers trusted. Anything connecting directly gets its socket address, so a client
    cannot pick its own IP by sending headers.
    """
    peer = request.client.host if request.client else None
    if peer and _is_private(peer):
        for header in ("cf-connecting-ip", "x-real-ip"):
            value = request.headers.get(header)
            if value:
                return value.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


_PROXY_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "::1/128", "fc00::/7")
)


def _is_private(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in _PROXY_NETWORKS)


async def too_many(key: str, limit: int) -> bool:
    try:
        value = await redis_client.get(f"xb:rl:{key}")
    except Exception:
        return False
    return value is not None and int(value) >= limit


async def count_failure(key: str, window_seconds: int) -> None:
    try:
        full_key = f"xb:rl:{key}"
        count = await redis_client.incr(full_key)
        if count == 1:
            await redis_client.expire(full_key, window_seconds)
    except Exception:
        pass


async def clear(key: str) -> None:
    try:
        await redis_client.delete(f"xb:rl:{key}")
    except Exception:
        pass


async def guard(*keys_and_limits: tuple[str, int], message: str = "Too many attempts. Try again later.") -> None:
    for key, limit in keys_and_limits:
        if await too_many(key, limit):
            raise AppError("too_many_attempts", message, 429)


async def hit(key: str, limit: int, window_seconds: int, message: str = "Too many requests. Try again later.") -> None:
    """Count every call (not just failures) and refuse once the window's limit is reached."""
    if await too_many(key, limit):
        raise AppError("too_many_requests", message, 429)
    await count_failure(key, window_seconds)
