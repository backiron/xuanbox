"""Tidy OCR text from a photo into a readable note, using the same local model as document recognition.

The model only rearranges what was read: a result that drops most of the text or brings numbers that
are not in the OCR text is thrown away, and the caller keeps the raw text instead.
"""

import asyncio
import json
import re
import time
from urllib import error, request

from app.core.config import settings
from app.services.ai_health_service import is_blank_ai_value, record_ai_result
from app.services.receipt_ai_service import _extract_json_object

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
LIST_PREFIX = re.compile(r"^\s*\d{1,2}[.、)]\s+", re.MULTILINE)
MAX_TITLE_CHARS = 60


def _ollama_note_chat(raw_text: str) -> dict:
    payload = {
        "model": settings.DOCUMENT_AI_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You turn OCR text from a photo or screenshot into a tidy plain-text note. Return JSON only: "
                    '{"title": short title, "body": the note text}. Write in the language of the text. '
                    "Keep every piece of real content and every number exactly as read; never add, guess or convert "
                    "quantities. Drop screen clutter such as status bars, clock times, battery, buttons and app menus. "
                    "Put each item on its own line; for lists of things with amounts, such as recipe ingredients, "
                    "write one 'name: amount' per line. Plain text only: no Markdown, no tables, no numbered lists. "
                    "Fix an OCR mistake only when the right word is obvious."
                ),
            },
            {"role": "user", "content": raw_text[: settings.DOCUMENT_AI_MAX_CHARS]},
        ],
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
            "num_predict": 1500,
        },
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


def accept_tidy_result(raw_text: str, result: dict) -> tuple[str, str] | None:
    """Return (title, body) when the model kept to the text it was given, otherwise None."""
    title = result.get("title")
    body = result.get("body")
    if isinstance(body, list):
        body = "\n".join(str(line) for line in body)
    if is_blank_ai_value(body) or not isinstance(body, str):
        return None
    body = "\n".join(line.rstrip() for line in body.strip().splitlines()).strip()
    title = "" if is_blank_ai_value(title) else re.sub(r"\s+", " ", str(title)).strip()[:MAX_TITLE_CHARS]
    raw_chars = len(re.sub(r"\s+", "", raw_text))
    if len(re.sub(r"\s+", "", body)) < raw_chars * 0.25:
        return None
    known = set(NUMBER.findall(raw_text))
    if any(number not in known for number in NUMBER.findall(LIST_PREFIX.sub("", f"{title}\n{body}"))):
        return None
    return title, body


async def tidy_note_text(raw_text: str) -> tuple[str, str] | None:
    if not settings.DOCUMENT_AI_ENABLED:
        return None
    started = time.monotonic()
    try:
        result = await asyncio.to_thread(_ollama_note_chat, raw_text)
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
        await record_ai_result("note", False, time.monotonic() - started, f"{type(exc).__name__}: {exc}")
        return None
    await record_ai_result("note", True, time.monotonic() - started)
    return accept_tidy_result(raw_text, result)
