import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from app.core.config import settings
from tests.conftest import BASE_URL


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"models": [{"name": "qwen2.5:3b"}]})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        content = {"document_type": "Warranty", "issuer": "Dyson", "counterparty": "None", "amount": "null", "keywords": ["warranty", "None"]}
        self._send({"message": {"content": json.dumps(content)}})


def run(coro):
    async def wrapper():
        from app.core.redis import redis_client

        try:
            return await coro
        finally:
            await redis_client.aclose()

    return asyncio.run(wrapper())


def test_ai_probe_records_and_cleans(monkeypatch):
    from app.services.ai_health_service import AI_STATE_KEY, ai_call_state, probe_ai
    from app.services.document_ai_service import enhance_document_parse

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setattr(settings, "DOCUMENT_AI_ENABLED", True)
    monkeypatch.setattr(settings, "DOCUMENT_AI_BASE_URL", url)
    monkeypatch.setattr(settings, "DOCUMENT_AI_MODEL", "qwen2.5:3b")
    monkeypatch.setattr(settings, "RECEIPT_AI_MODEL", "qwen2.5:3b")

    async def online():
        from app.core.redis import redis_client

        await redis_client.delete(AI_STATE_KEY)
        probe = await probe_ai()
        parsed = await enhance_document_parse("warranty text", {}, "other")
        return probe, parsed, await ai_call_state()

    probe, parsed, state = run(online())
    server.shutdown()
    assert probe["status"] == "ok" and probe["model_installed"] is True
    assert parsed == {"document_type": "Warranty", "issuer": "Dyson", "keywords": ["warranty"]}
    assert state["ok_count"] == 1 and state["last_ok_kind"] == "document"

    monkeypatch.setattr(settings, "DOCUMENT_AI_BASE_URL", "http://127.0.0.1:9")

    async def offline():
        return await probe_ai(), await enhance_document_parse("text", {}, "other"), await ai_call_state()

    probe, parsed, state = run(offline())
    assert probe["status"] == "offline" and probe["probe_error"]
    assert parsed == {}
    assert state["error_count"] == 1 and state["last_error_kind"] == "document"


def test_admin_worker_reports_ai_status(open_registration):
    login = httpx.post(f"{BASE_URL}/auth/admin-login", json={"username_or_email": "owner", "password": "owner-password-123"})
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    worker = httpx.get(f"{BASE_URL}/admin/worker", headers=headers).json()["data"]
    # The test stack has AI switched off, so it must say so instead of pretending to be fine.
    assert worker["ai"]["status"] == "disabled"
    overview = httpx.get(f"{BASE_URL}/admin/overview", headers=headers).json()["data"]
    assert overview["service_status"]["ai"] == "disabled"
    assert overview["service_status"]["redis"] == "ok"
