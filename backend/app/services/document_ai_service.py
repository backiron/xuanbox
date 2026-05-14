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


def _ollama_document_chat(raw_text: str, current_parse: dict, detected_type: str) -> dict:
    payload = {
        "model": settings.DOCUMENT_AI_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You classify private personal documents from already extracted text. "
                    "Return compact JSON only. Do not invent facts. Use null when unsure."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "ocr_text": raw_text[: settings.DOCUMENT_AI_MAX_CHARS],
                        "current_detected_type": detected_type,
                        "current_parse": current_parse,
                        "wanted_fields": [
                            "document_type",
                            "title",
                            "summary",
                            "issuer",
                            "counterparty",
                            "primary_date",
                            "amount",
                            "currency",
                            "warranty_until",
                            "serial_number",
                            "keywords",
                            "labels",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{settings.DOCUMENT_AI_BASE_URL.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=settings.DOCUMENT_AI_TIMEOUT_SECONDS) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    content = (response_payload.get("message") or {}).get("content") or ""
    return _extract_json_object(content)


def _clean_ai_payload(payload: dict) -> dict:
    allowed = {
        "document_type",
        "title",
        "summary",
        "issuer",
        "counterparty",
        "primary_date",
        "amount",
        "currency",
        "warranty_until",
        "serial_number",
        "keywords",
        "labels",
    }
    cleaned: dict = {}
    for key, value in payload.items():
        if key not in allowed or value in ("", [], {}):
            continue
        if key in {"keywords", "labels"}:
            if isinstance(value, list):
                cleaned[key] = [str(item).strip()[:80] for item in value if str(item).strip()][:12]
            continue
        cleaned[key] = str(value).strip()[:4000 if key == "summary" else 255]
    return cleaned


async def enhance_document_parse(raw_text: str, current_parse: dict, detected_type: str) -> dict:
    if not settings.DOCUMENT_AI_ENABLED:
        return {}
    try:
        payload = await asyncio.to_thread(_ollama_document_chat, raw_text, current_parse, detected_type)
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError):
        return {}
    return _clean_ai_payload(payload)
