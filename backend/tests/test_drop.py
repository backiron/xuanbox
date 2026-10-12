import asyncio
import json
import os
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from tests.conftest import BASE_URL, WS_URL, Device


def png_bytes(size=(800, 600), color=(30, 120, 220)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def self_thread_id(device: Device) -> str:
    threads = device.data(device.get("/drop/threads"))
    return next(thread["id"] for thread in threads if thread["kind"] == "self")


def open_socket(device: Device):
    ticket = device.data(device.post("/drop/ws-ticket"))["ticket"]
    return connect(f"{WS_URL}/drop/ws?ticket={ticket}", open_timeout=5)


def wait_for_event(socket, event: str, timeout: float = 5.0, predicate=lambda data: True) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        message = json.loads(socket.recv(timeout=max(deadline - time.time(), 0.05)))
        if message.get("event") == event and predicate(message.get("data")):
            return message.get("data")
    raise AssertionError(f"event {event} not received")


# ---------------------------------------------------------------- devices


def test_same_browser_reuses_device_and_new_browser_adds_one(make_user):
    phone = make_user("dev")
    phone.login()  # same device key again
    me = phone.data(phone.get("/drop/me"))
    assert len(me["devices"]) == 1
    assert me["devices"][0]["is_current"] is True

    laptop = phone.another_device("Laptop")
    me = laptop.data(laptop.get("/drop/me"))
    assert len(me["devices"]) == 2
    current = next(device for device in me["devices"] if device["is_current"])
    assert current["device_name"] == "Laptop"

    renamed = laptop.data(laptop.patch(f"/drop/devices/{current['id']}", json={"device_name": "我的电脑"}))
    assert renamed["device_name"] == "我的电脑"


def test_generic_name_is_upgraded_and_other_devices_can_be_removed(make_user):
    phone = make_user("gen", device_name="Local Browser")
    phone.login("iPhone · Safari")
    me = phone.data(phone.get("/drop/me"))
    assert [device["device_name"] for device in me["devices"]] == ["iPhone · Safari"]

    laptop = phone.another_device("Windows · Chrome")
    laptop_id = laptop.data(laptop.get("/drop/me"))["current_device_id"]
    phone_id = me["current_device_id"]
    assert phone.delete(f"/drop/devices/{phone_id}").status_code == 400
    phone.data(phone.delete(f"/drop/devices/{laptop_id}"))
    assert laptop.get("/drop/threads").status_code == 401
    assert [device["id"] for device in phone.data(phone.get("/drop/me"))["devices"]] == [phone_id]


def test_signed_out_session_cannot_use_drop(make_user):
    device = make_user("revoked")
    assert device.get("/drop/threads").status_code == 200
    httpx.post(f"{BASE_URL}/auth/logout", headers=device.headers, json={"refresh_token": device.tokens["refresh_token"]}).raise_for_status()
    response = device.get("/drop/threads")
    assert response.status_code == 401
    assert response.json()["error_code"] == "session_revoked"


# ---------------------------------------------------------------- own devices


def test_text_between_own_devices_with_unread_counts(make_user):
    phone = make_user("self", device_name="Phone")
    laptop = phone.another_device("Laptop")
    thread_id = self_thread_id(phone)
    laptop_id = laptop.data(laptop.get("/drop/me"))["current_device_id"]

    sent = phone.data(phone.post(f"/drop/threads/{thread_id}/messages", json={"body": "https://example.com/link", "target_device_id": laptop_id, "client_id": "c1"}))
    assert sent["kind"] == "text"
    assert sent["target_device_id"] == laptop_id
    assert sent["client_id"] == "c1"

    messages = laptop.data(laptop.get(f"/drop/threads/{thread_id}/messages"))
    assert [message["body"] for message in messages] == ["https://example.com/link"]

    laptop_thread = next(thread for thread in laptop.data(laptop.get("/drop/threads")) if thread["id"] == thread_id)
    phone_thread = next(thread for thread in phone.data(phone.get("/drop/threads")) if thread["id"] == thread_id)
    assert laptop_thread["unread_count"] == 1
    assert phone_thread["unread_count"] == 0

    laptop.data(laptop.post(f"/drop/threads/{thread_id}/read"))
    laptop_thread = next(thread for thread in laptop.data(laptop.get("/drop/threads")) if thread["id"] == thread_id)
    assert laptop_thread["unread_count"] == 0


def test_cannot_target_someone_elses_device(make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    bob_device = bob.data(bob.get("/drop/me"))["current_device_id"]
    response = alice.post(f"/drop/threads/{self_thread_id(alice)}/messages", json={"body": "hi", "target_device_id": bob_device})
    assert response.status_code == 400


def test_image_transfer_download_thumbnail_and_save(make_user):
    phone = make_user("img")
    laptop = phone.another_device()
    thread_id = self_thread_id(phone)
    original = png_bytes()

    sent = phone.data(phone.post(f"/drop/threads/{thread_id}/files", files={"file": ("照片.png", original, "image/png")}))
    assert sent["has_thumbnail"] is True
    assert (sent["image_width"], sent["image_height"]) == (800, 600)
    assert sent["filename"] == "照片.png"

    download = laptop.get(f"/drop/messages/{sent['id']}/download")
    assert download.status_code == 200
    assert download.content == original

    thumbnail = laptop.get(f"/drop/messages/{sent['id']}/thumbnail")
    assert thumbnail.status_code == 200
    assert Image.open(BytesIO(thumbnail.content)).size[0] <= 480

    saved = laptop.data(laptop.post(f"/drop/messages/{sent['id']}/save", json={"destination": "photos"}))
    assert saved["saved_to"] == "photos"
    again = laptop.data(laptop.post(f"/drop/messages/{sent['id']}/save", json={"destination": "photos"}))
    assert again["saved_to"] == "photos"
    photos = laptop.data(laptop.get("/photos"))
    assert len(photos) == 1

    listed = laptop.data(laptop.get(f"/drop/threads/{thread_id}/messages"))
    assert listed[0]["saved_to"] == "photos"


def test_non_image_cannot_be_saved_as_photo(make_user):
    device = make_user("doc")
    thread_id = self_thread_id(device)
    sent = device.data(device.post(f"/drop/threads/{thread_id}/files", files={"file": ("notes.txt", b"hello", "text/plain")}))
    assert sent["has_thumbnail"] is False
    assert device.post(f"/drop/messages/{sent['id']}/save", json={"destination": "photos"}).status_code == 400
    assert device.data(device.post(f"/drop/messages/{sent['id']}/save", json={"destination": "files"}))["saved_to"] == "files"


def test_other_users_cannot_reach_my_conversation(make_user):
    owner = make_user("owner")
    stranger = make_user("stranger")
    thread_id = self_thread_id(owner)
    sent = owner.data(owner.post(f"/drop/threads/{thread_id}/files", files={"file": ("secret.txt", b"secret", "text/plain")}))

    assert stranger.get(f"/drop/threads/{thread_id}/messages").status_code == 404
    assert stranger.post(f"/drop/threads/{thread_id}/messages", json={"body": "x"}).status_code == 404
    assert stranger.get(f"/drop/messages/{sent['id']}/download").status_code == 404
    assert stranger.post(f"/drop/messages/{sent['id']}/save", json={"destination": "files"}).status_code == 404
    assert stranger.delete(f"/drop/messages/{sent['id']}").status_code == 404


def test_attachment_is_encrypted_on_disk_and_removed_on_delete(make_user):
    device = make_user("disk")
    thread_id = self_thread_id(device)
    marker = b"plaintext-marker-" * 64
    sent = device.data(device.post(f"/drop/threads/{thread_id}/files", files={"file": ("m.bin", marker, "application/octet-stream")}))
    stored = list((Path(os.environ["STORAGE_ROOT"]) / "encrypted_drop" / thread_id).glob(f"{sent['id']}*"))
    assert len(stored) == 1
    assert b"plaintext-marker" not in stored[0].read_bytes()

    device.data(device.delete(f"/drop/messages/{sent['id']}"))
    assert not stored[0].exists()
    assert device.get(f"/drop/messages/{sent['id']}/download").status_code == 404


# ---------------------------------------------------------------- contacts and family conversations


def test_direct_conversation_requires_accepted_contact(make_user):
    mom = make_user("mom")
    kid = make_user("kid")
    kid_id = kid.data(kid.get("/drop/me"))["user"]["id"]
    mom_id = mom.data(mom.get("/drop/me"))["user"]["id"]

    assert mom.post("/drop/threads/direct", json={"user_id": kid_id}).status_code == 403
    assert mom.post("/drop/contacts", json={"identifier": "nobody-here"}).status_code == 404
    assert mom.post("/drop/contacts", json={"identifier": mom.username}).status_code == 400

    request = mom.data(mom.post("/drop/contacts", json={"identifier": kid.username}))
    assert request["status"] == "pending" and request["direction"] == "outgoing"
    assert mom.post(f"/drop/contacts/{request['id']}/accept").status_code == 400  # only the addressee can accept
    assert mom.post("/drop/threads/direct", json={"user_id": kid_id}).status_code == 403

    incoming = kid.data(kid.get("/drop/contacts"))
    assert incoming[0]["direction"] == "incoming" and incoming[0]["peer"]["username"] == mom.username
    kid.data(kid.post(f"/drop/contacts/{request['id']}/accept"))

    thread = mom.data(mom.post("/drop/threads/direct", json={"user_id": kid_id}))
    same = kid.data(kid.post("/drop/threads/direct", json={"user_id": mom_id}))
    assert thread["id"] == same["id"]

    sent = mom.data(mom.post(f"/drop/threads/{thread['id']}/files", files={"file": ("receipt.png", png_bytes(), "image/png")}))
    assert kid.get(f"/drop/messages/{sent['id']}/download").status_code == 200
    kid_thread = next(item for item in kid.data(kid.get("/drop/threads")) if item["id"] == thread["id"])
    assert kid_thread["unread_count"] == 1 and kid_thread["peer"]["username"] == mom.username

    # Only the sender can delete; the receiver keeps a private copy by saving it.
    assert kid.delete(f"/drop/messages/{sent['id']}").status_code == 403
    kid.data(kid.post(f"/drop/messages/{sent['id']}/save", json={"destination": "receipts", "merchant": "Costco"}))
    receipts = kid.data(kid.get("/receipts"))
    assert receipts[0]["merchant"] == "Costco"
    assert mom.data(mom.get("/receipts")) == []

    outsider = make_user("outsider")
    assert outsider.get(f"/drop/threads/{thread['id']}/messages").status_code == 404

    mom.data(mom.delete(f"/drop/contacts/{request['id']}"))
    assert mom.post(f"/drop/threads/{thread['id']}/messages", json={"body": "still there?"}).status_code == 403
    assert mom.get(f"/drop/threads/{thread['id']}/messages").status_code == 200


def test_asking_back_accepts_a_pending_request(make_user):
    first = make_user("first")
    second = make_user("second")
    first.data(first.post("/drop/contacts", json={"identifier": second.username}))
    contact = second.data(second.post("/drop/contacts", json={"identifier": f"{first.username}@example.com".upper()}))
    assert contact["status"] == "accepted"


# ---------------------------------------------------------------- realtime


def test_websocket_delivers_messages_and_presence(make_user):
    phone = make_user("ws", device_name="Phone")
    laptop = phone.another_device("Laptop")
    thread_id = self_thread_id(phone)
    phone_id = phone.data(phone.get("/drop/me"))["current_device_id"]

    with open_socket(laptop) as laptop_socket:
        with open_socket(phone):
            presence = wait_for_event(laptop_socket, "presence", predicate=lambda data: data["device_id"] == phone_id)
            assert presence["online"] is True
            devices = laptop.data(laptop.get("/drop/me"))["devices"]
            assert {device["online"] for device in devices} == {True}

            phone.data(phone.post(f"/drop/threads/{thread_id}/messages", json={"body": "instant"}))
            created = wait_for_event(laptop_socket, "message.created")
            assert created["body"] == "instant" and created["sender_device_id"] == phone_id

        offline = wait_for_event(laptop_socket, "presence", predicate=lambda data: data["device_id"] == phone_id and not data["online"])
        assert offline["online"] is False

        laptop_socket.send("ping")
        wait_for_event(laptop_socket, "pong")


def test_websocket_ticket_is_single_use_and_scoped_to_user(make_user):
    alice = make_user("wsa")
    bob = make_user("wsb")
    ticket = alice.data(alice.post("/drop/ws-ticket"))["ticket"]
    with connect(f"{WS_URL}/drop/ws?ticket={ticket}", open_timeout=5) as alice_socket:
        try:
            with connect(f"{WS_URL}/drop/ws?ticket={ticket}", open_timeout=5) as reused:
                reused.recv(timeout=3)
            raise AssertionError("reused ticket was accepted")
        except (ConnectionClosed, Exception) as exc:  # rejected handshake or immediate close
            assert not isinstance(exc, AssertionError)

        bob.data(bob.post(f"/drop/threads/{self_thread_id(bob)}/messages", json={"body": "bob only"}))
        try:
            message = json.loads(alice_socket.recv(timeout=1.5))
            assert message.get("event") != "message.created"
        except TimeoutError:
            pass


# ---------------------------------------------------------------- QR upload and expiry


def test_qr_upload_lands_in_my_devices_conversation(make_user):
    device = make_user("qr")
    session = device.data(device.post("/drop/sessions", json={"title": "Desk", "expires_in_minutes": 5}))
    response = httpx.post(f"{BASE_URL}/drop/public/{session['token']}/upload", files={"file": ("scan.txt", b"from qr", "text/plain")})
    assert response.status_code == 200, response.text

    messages = device.data(device.get(f"/drop/threads/{self_thread_id(device)}/messages"))
    assert messages[-1]["sender_label"] == "QR · Desk"
    assert messages[-1]["sender_device_id"] is None
    assert device.get(f"/drop/messages/{messages[-1]['id']}/download").content == b"from qr"


def test_expired_messages_are_hidden_and_cleaned_up(make_user):
    import psycopg
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.services.drop_service import cleanup_expired_messages

    device = make_user("exp")
    thread_id = self_thread_id(device)
    sent = device.data(device.post(f"/drop/threads/{thread_id}/files", files={"file": ("old.txt", b"old", "text/plain")}))
    blob = next((Path(os.environ["STORAGE_ROOT"]) / "encrypted_drop" / thread_id).glob(f"{sent['id']}*"))

    with psycopg.connect(settings.sync_database_url.replace("postgresql+psycopg", "postgresql")) as connection:
        connection.execute("UPDATE drop_messages SET expires_at = now() - interval '1 minute' WHERE id = %s", (sent["id"],))

    assert device.data(device.get(f"/drop/threads/{thread_id}/messages")) == []
    assert device.get(f"/drop/messages/{sent['id']}/download").status_code == 404

    async def run_cleanup() -> int:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            removed = await cleanup_expired_messages(session)
        await engine.dispose()
        return removed

    assert asyncio.run(run_cleanup()) >= 1
    assert not blob.exists()
