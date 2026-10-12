"""Redis-backed fan-out for XuanDrop realtime events.

Every user has one pub/sub channel. A WebSocket connection subscribes to its user's channel and forwards
events to the browser; any API process can publish. Device presence is a Redis key per device with a TTL
that the connection refreshes while it is alive.
"""

import json
import secrets
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.redis import redis_client

PRESENCE_TTL_SECONDS = 70
WS_TICKET_TTL_SECONDS = 60


def user_channel(user_id: UUID | str) -> str:
    return f"xb:drop:user:{user_id}"


def presence_key(device_id: UUID | str) -> str:
    return f"xb:drop:presence:{device_id}"


def _ticket_key(ticket: str) -> str:
    return f"xb:drop:ws-ticket:{ticket}"


async def publish_to_users(user_ids: Iterable[UUID | str], event: str, data: Any) -> None:
    message = json.dumps({"event": event, "data": data}, default=str)
    for user_id in {str(user_id) for user_id in user_ids}:
        await redis_client.publish(user_channel(user_id), message)


async def mark_device_online(device_id: UUID | str, connection_id: str) -> None:
    await redis_client.set(presence_key(device_id), connection_id, ex=PRESENCE_TTL_SECONDS)


async def mark_device_offline(device_id: UUID | str, connection_id: str) -> bool:
    """Clear presence only if this connection still owns it, so a reconnect is not marked offline."""
    key = presence_key(device_id)
    if await redis_client.get(key) == connection_id:
        await redis_client.delete(key)
        return True
    return False


async def online_device_ids(device_ids: Iterable[UUID | str]) -> set[str]:
    ids = [str(device_id) for device_id in device_ids]
    if not ids:
        return set()
    values = await redis_client.mget([presence_key(device_id) for device_id in ids])
    return {device_id for device_id, value in zip(ids, values) if value}


async def issue_ws_ticket(payload: dict[str, str]) -> str:
    ticket = secrets.token_urlsafe(32)
    await redis_client.set(_ticket_key(ticket), json.dumps(payload), ex=WS_TICKET_TTL_SECONDS)
    return ticket


async def redeem_ws_ticket(ticket: str) -> dict[str, str] | None:
    raw = await redis_client.getdel(_ticket_key(ticket))
    return json.loads(raw) if raw else None
