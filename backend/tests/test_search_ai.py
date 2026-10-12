import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from app.core.config import settings
from tests.conftest import BASE_URL
from tests.test_receipt_ocr import run_worker_until_idle

# A toy embedding: one dimension per concept, so "meaning" is predictable in tests.
CONCEPTS = {
    "car": ("car", "repair", "oil", "midas", "tire", "修车", "汽车"),
    "food": ("costco", "grocery", "groceries", "milk", "bread", "超市", "买菜"),
    "travel": ("hotel", "flight", "airline", "机票"),
}


class FakeEmbeddings(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        vectors = []
        for text in body["input"]:
            lower = text.lower()
            vectors.append([float(sum(lower.count(word) for word in words)) + 0.01 for words in CONCEPTS.values()])
        payload = json.dumps({"embeddings": vectors}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def run(coro):
    from app.core.database import engine
    from app.core.redis import redis_client

    async def wrapper():
        try:
            return await coro
        finally:
            await engine.dispose()
            await redis_client.aclose()

    return asyncio.run(wrapper())


def make_pro(device):
    login = httpx.post(f"{BASE_URL}/auth/admin-login", json={"username_or_email": "owner", "password": "owner-password-123"})
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    user_id = device.data(device.get("/auth/me"))["id"]
    httpx.patch(f"{BASE_URL}/admin/users/{user_id}", headers=headers, json={"plan": "pro"}).raise_for_status()


def search(device, query):
    from app.models.user import User
    from app.core.database import AsyncSessionLocal
    from app.services.search_service import search_all

    async def go():
        async with AsyncSessionLocal() as db:
            user = await db.scalar(__import__("sqlalchemy").select(User).where(User.username == device.username))
            response = await search_all(db, user, query)
            return [item for item in response.results if item.type == "semantic"]

    return run(go())


def test_search_by_meaning_end_to_end(make_user, monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeEmbeddings)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(settings, "SEARCH_AI_ENABLED", True)
    monkeypatch.setattr(settings, "DOCUMENT_AI_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}")

    pro, free, other_pro = make_user("sem"), make_user("semfree"), make_user("semother")
    make_pro(pro)
    make_pro(other_pro)
    car = pro.data(pro.post("/receipts/upload", files={"file": ("a.txt", b"MIDAS AUTO\nOil change and tire rotation\nTOTAL 89.99 CAD", "text/plain")}))
    food = pro.data(pro.post("/receipts/upload", files={"file": ("b.txt", b"COSTCO WHOLESALE\nMILK 5.49\nBREAD 3.29\nTOTAL 8.78 CAD", "text/plain")}))
    free.data(free.post("/receipts/upload", files={"file": ("c.txt", b"MIDAS AUTO\nOil change\nTOTAL 50.00 CAD", "text/plain")}))

    # OCR runs, its completion hook queues indexing, then the worker embeds the receipts.
    run_worker_until_idle()
    run_worker_until_idle()

    by_chinese = search(pro, "去年修车的发票")
    assert [item.id for item in by_chinese] == [__import__("uuid").UUID(car["id"])]
    assert by_chinese[0].target_type == "receipt" and by_chinese[0].title
    assert [str(item.id) for item in search(pro, "超市买菜")] == [food["id"]]
    assert search(pro, "机票 hotel") == []  # nothing about travel: no forced matches

    assert search(free, "修车") == []  # no AI search on the free plan
    assert search(other_pro, "修车") == []  # never another person's receipts

    pro.data(pro.delete(f"/receipts/{car['id']}"))
    assert search(pro, "修车") == []
    server.shutdown()
