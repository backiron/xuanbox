import asyncio
import json
import time
from urllib import error, request

from app.core.config import settings
from app.services.ai_health_service import is_blank_ai_value, record_ai_result


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
                    "Prefer the store or restaurant brand as merchant. Do not use slogans, addresses, phone numbers, "
                    "table numbers, payment sections, or item names as merchant. Return null when the merchant is not visible. "
                    "Infer category from receipt context and items when possible, such as groceries, restaurant, fuel, "
                    "pharmacy, electronics, clothing, office, travel, home, or other. Treat clear return, refund, exchange, "
                    "or warranty periods as warranty_until by adding the period to purchase_date. Never invent amounts or dates. "
                    "List every purchased line in items: name exactly as printed; kind = what the product or service is in "
                    "a few plain English words (for example leather boots, paper towels, rotisserie chicken, oil change), "
                    "only when the name or store makes it reasonably clear, otherwise null; quantity as a number; price as printed. "
                    "Skip subtotal, tax, discount, payment and change lines."
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
                            "items",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
            "num_predict": 1200,
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
    started = time.monotonic()
    try:
        result = await asyncio.to_thread(_ollama_chat, raw_text, parsed)
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
        await record_ai_result("receipt", False, time.monotonic() - started, f"{type(exc).__name__}: {exc}")
        return {}
    await record_ai_result("receipt", True, time.monotonic() - started)
    cleaned = {key: value for key, value in result.items() if not is_blank_ai_value(value) and key not in {"items", "items_summary"}}
    items = normalize_items(result.get("items"))
    if items:
        cleaned["items"] = items
        cleaned["items_summary"] = items_summary(items)
    return cleaned


MAX_ITEMS = 40


def normalize_items(value) -> list[dict]:
    """Keep well-formed item lines only; the model sometimes returns strings, nulls or totals."""
    if not isinstance(value, list):
        return []
    items = []
    for raw in value[:MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("item_name") or "").strip()
        if is_blank_ai_value(name):
            continue
        kind = raw.get("kind")
        quantity = raw.get("quantity")
        price = raw.get("price") if raw.get("price") is not None else raw.get("total_price")
        items.append(
            {
                "name": name[:120],
                "kind": None if is_blank_ai_value(kind) else str(kind).strip()[:60],
                "quantity": quantity if isinstance(quantity, (int, float)) and not isinstance(quantity, bool) else None,
                "price": None if is_blank_ai_value(price) else str(price).strip()[:20],
            }
        )
    return items


def items_summary(items: list[dict]) -> str:
    """Readable one-liner used in the review screen and in meaning-based search."""
    parts = []
    for item in items:
        text = item["name"]
        if item.get("kind") and item["kind"].lower() not in text.lower():
            text += f" ({item['kind']})"
        if item.get("quantity") and item["quantity"] != 1:
            text += f" ×{item['quantity']:g}"
        if item.get("price"):
            text += f" {item['price']}"
        parts.append(text)
    return "; ".join(parts)[:1000]
