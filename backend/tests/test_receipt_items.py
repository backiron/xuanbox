import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.core.config import settings
from tests.test_ai_health import run

MODEL_REPLY = {
    "merchant": "Red Wing Shoe Store",
    "amount": 482.99,
    "items": [
        {"name": "RW -Heritage Norway Moc", "kind": "leather boots", "quantity": 1, "price": "459.99"},
        {"name": "Mink oil", "kind": None, "quantity": 2, "price": "11.50"},
        {"name": "None", "kind": "tax", "price": "23.00"},
        "Sub Total 459.99",
        {"item_name": "Laces", "total_price": "4.00"},
    ],
}


class FakeChat(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps({"message": {"content": json.dumps(MODEL_REPLY)}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_items_are_listed_with_what_they_are(monkeypatch):
    from app.services.ocr_service import _merge_ai_fields
    from app.services.receipt_ai_service import enhance_receipt_parse

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeChat)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(settings, "RECEIPT_AI_ASSIST_ENABLED", True)
    monkeypatch.setattr(settings, "RECEIPT_AI_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}")
    result = run(enhance_receipt_parse("receipt text", {}))
    server.shutdown()

    assert [item["name"] for item in result["items"]] == ["RW -Heritage Norway Moc", "Mink oil", "Laces"]
    assert result["items"][0]["kind"] == "leather boots"
    assert result["items"][2]["price"] == "4.00"
    assert result["items_summary"] == "RW -Heritage Norway Moc (leather boots) 459.99; Mink oil ×2 11.50; Laces 4.00"
    merged = _merge_ai_fields({"merchant": None}, result)
    assert merged["items"][0]["kind"] == "leather boots" and merged["ai_assisted"] is True


def test_saving_inbox_item_as_receipt_returns_where_to_open_it(make_user):
    device = make_user("inb")
    item = device.data(device.post("/inbox/upload", files={"file": ("r.txt", b"SHOP\nTOTAL 1.00", "text/plain")}))
    resolved = device.data(device.post(f"/inbox/{item['id']}/resolve", json={"action": "receipt"}))
    receipts = device.data(device.get("/receipts"))
    assert resolved["receipt_id"] == receipts[0]["id"]
    photo_item = device.data(device.post("/inbox/upload", files={"file": ("n.txt", b"note", "text/plain")}))
    dismissed = device.data(device.post(f"/inbox/{photo_item['id']}/resolve", json={"action": "dismiss"}))
    assert dismissed["receipt_id"] is None
