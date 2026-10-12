"""Visibility for the optional local AI (Ollama).

AI calls fall back to rules silently by design, so every call records its outcome here and the admin
console shows whether AI is actually reachable and when it last worked.
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from urllib import request

from app.core.config import settings
from app.core.redis import redis_client

AI_STATE_KEY = "xb:ai:state"
NULL_STRINGS = {"", "none", "null", "n/a", "na", "unknown", "nil"}


def is_blank_ai_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NULL_STRINGS
    return value in ([], {})


async def record_ai_result(kind: str, ok: bool, seconds: float, error: str | None = None) -> None:
    now = datetime.now(UTC).isoformat()
    try:
        if ok:
            await redis_client.hset(AI_STATE_KEY, mapping={"last_ok_at": now, "last_ok_kind": kind, "last_ok_seconds": f"{seconds:.1f}"})
            await redis_client.hincrby(AI_STATE_KEY, "ok_count", 1)
        else:
            await redis_client.hset(AI_STATE_KEY, mapping={"last_error_at": now, "last_error_kind": kind, "last_error": (error or "unknown")[:300]})
            await redis_client.hincrby(AI_STATE_KEY, "error_count", 1)
    except Exception:
        # Status bookkeeping must never break the upload pipeline.
        pass


async def ai_call_state() -> dict:
    try:
        state = await redis_client.hgetall(AI_STATE_KEY)
    except Exception:
        return {}
    for key in ("ok_count", "error_count"):
        state[key] = int(state.get(key, 0))
    return state


def _fetch_tags(base_url: str) -> list[str]:
    with request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [model.get("name", "") for model in payload.get("models", [])]


async def probe_ai() -> dict:
    enabled = settings.DOCUMENT_AI_ENABLED or settings.RECEIPT_AI_ASSIST_ENABLED
    result = {
        "enabled": enabled,
        "model": settings.DOCUMENT_AI_MODEL,
        "receipt_model": settings.RECEIPT_AI_MODEL,
        "base_url": settings.DOCUMENT_AI_BASE_URL,
        "status": "disabled",
        "reachable": False,
        "model_installed": False,
        "latency_ms": None,
        "probe_error": None,
    }
    if not enabled:
        return result
    started = time.monotonic()
    try:
        models = await asyncio.to_thread(_fetch_tags, settings.DOCUMENT_AI_BASE_URL)
    except Exception as exc:
        result.update(status="offline", probe_error=f"{type(exc).__name__}: {exc}"[:300])
        return result
    result["latency_ms"] = int((time.monotonic() - started) * 1000)
    result["reachable"] = True
    wanted = {settings.DOCUMENT_AI_MODEL, settings.RECEIPT_AI_MODEL}
    result["model_installed"] = wanted.issubset(set(models))
    result["status"] = "ok" if result["model_installed"] else "model_missing"
    return result
