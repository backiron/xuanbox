import asyncio
import json
from urllib import error, request

from app.core.config import settings


def _extract_json_object(value: str) -> dict:
    value = value.strip()
    if value.startswith("```"):
        value = value.strip("`")
        if value.lower().startswith("json"):
            value = value[4:].strip()
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(value[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ollama_chat(raw_text: str, parsed: dict) -> dict:
    payload = {
        "model": settings.RECEIPT_AI_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract receipt metadata from OCR text. Return compact JSON only. "
                    "Use null when unsure. Never invent amounts, dates, or merchants."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "ocr_text": raw_text[: settings.RECEIPT_AI_MAX_CHARS],
                        "current_parse": parsed,
                        "wanted_fields": [
                            "merchant",
                            "category",
                            "amount",
                            "currency",
                            "purchase_date",
                            "warranty_until",
                            "notes",
                            "items_summary",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{settings.RECEIPT_AI_BASE_URL.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=settings.RECEIPT_AI_TIMEOUT_SECONDS) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    content = (response_payload.get("message") or {}).get("content") or ""
    return _extract_json_object(content)


async def enhance_receipt_parse(raw_text: str, parsed: dict) -> dict:
    if not settings.RECEIPT_AI_ASSIST_ENABLED:
        return {}
    try:
        return await asyncio.to_thread(_ollama_chat, raw_text, parsed)
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError):
        return {}
