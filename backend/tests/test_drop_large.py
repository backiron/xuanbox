import hashlib
import os
from pathlib import Path

import httpx

from tests.conftest import BASE_URL
from tests.test_drop import self_thread_id

MIB = 1024 * 1024


def start(device, thread_id, size, name="video.mp4", mime="video/mp4"):
    return device.post(f"/drop/threads/{thread_id}/uploads", json={"filename": name, "mime_type": mime, "file_size": size, "client_id": "big1"})


def put(device, upload_id, index, data):
    return httpx.put(f"{BASE_URL}/drop/uploads/{upload_id}/chunks/{index}", headers=device.headers, content=data, timeout=60)


def test_large_file_arrives_in_chunks_and_resumes(make_user):
    phone = make_user("big")
    laptop = phone.another_device()
    stranger = make_user("bigx")
    thread_id = self_thread_id(phone)
    payload = os.urandom(20 * MIB)
    upload = phone.data(start(phone, thread_id, len(payload)))
    chunk = upload["chunk_size"]
    assert chunk == 8 * MIB and upload["next_index"] == 0
    parts = [payload[i : i + chunk] for i in range(0, len(payload), chunk)]
    assert len(parts) == 3

    assert put(phone, upload["id"], 1, parts[1]).status_code == 409  # out of order
    assert put(phone, upload["id"], 0, parts[0][:-1]).status_code == 400  # wrong size
    assert put(stranger, upload["id"], 0, parts[0]).status_code == 404
    assert phone.data(put(phone, upload["id"], 0, parts[0]))["next_index"] == 1
    # A retried chunk after a dropped connection is accepted once, not appended twice.
    assert phone.data(put(phone, upload["id"], 0, parts[0]))["next_index"] == 1
    assert phone.post(f"/drop/uploads/{upload['id']}/complete").status_code == 400  # incomplete

    resumed = phone.data(phone.get(f"/drop/uploads/{upload['id']}"))
    assert resumed["next_index"] == 1 and resumed["received_bytes"] == chunk
    for index in range(resumed["next_index"], len(parts)):
        phone.data(put(phone, upload["id"], index, parts[index]))
    message = phone.data(phone.post(f"/drop/uploads/{upload['id']}/complete"))
    assert message["file_size"] == len(payload) and message["client_id"] == "big1"
    assert message["can_save_to_library"] is False

    stored = Path(os.environ["STORAGE_ROOT"]) / "encrypted_drop" / thread_id / f"{message['id']}.bin"
    with stored.open("rb") as handle:
        assert payload[: 64 * 1024] not in handle.read(9 * MIB)

    with httpx.stream("GET", f"{BASE_URL}/drop/messages/{message['id']}/download", headers=laptop.headers, timeout=60) as response:
        assert response.status_code == 200
        assert int(response.headers["content-length"]) == len(payload)
        digest = hashlib.sha256()
        for block in response.iter_bytes():
            digest.update(block)
    assert digest.hexdigest() == hashlib.sha256(payload).hexdigest()

    link = laptop.data(laptop.post(f"/drop/messages/{message['id']}/download-link"))["url"]
    native = httpx.get(f"{BASE_URL.removesuffix('/api/v1')}{link}", timeout=60)
    assert native.status_code == 200 and hashlib.sha256(native.content).digest() == hashlib.sha256(payload).digest()
    wrong_message = link.replace(message["id"], self_thread_id(phone))
    assert httpx.get(f"{BASE_URL.removesuffix('/api/v1')}{wrong_message}").status_code in (403, 404)
    assert stranger.post(f"/drop/messages/{message['id']}/download-link").status_code == 404

    saved = laptop.post(f"/drop/messages/{message['id']}/save", json={"destination": "files"})
    assert saved.status_code == 413 and saved.json()["error_code"] == "drop_too_large_for_library"


def test_upload_limits_and_cancel(make_user):
    device = make_user("lim")
    thread_id = self_thread_id(device)
    assert start(device, thread_id, 3 * 1024 * MIB).status_code == 413  # over the per-file limit
    upload = device.data(start(device, thread_id, 2 * MIB, name="a.bin", mime="application/octet-stream"))
    part = Path(os.environ["STORAGE_ROOT"]) / "encrypted_drop" / "_uploads" / f"{upload['id']}.part"
    device.data(put(device, upload["id"], 0, os.urandom(MIB) + os.urandom(MIB)))
    assert part.exists()
    device.data(device.delete(f"/drop/uploads/{upload['id']}"))
    assert not part.exists()
    assert device.get(f"/drop/uploads/{upload['id']}").status_code == 404


def test_small_files_still_work_and_both_formats_download(make_user):
    device = make_user("mix")
    thread_id = self_thread_id(device)
    small = device.data(device.post(f"/drop/threads/{thread_id}/files", files={"file": ("n.txt", b"small one", "text/plain")}))
    assert device.get(f"/drop/messages/{small['id']}/download").content == b"small one"
    upload = device.data(start(device, thread_id, 5, name="tiny.txt", mime="text/plain"))
    device.data(put(device, upload["id"], 0, b"hello"))
    chunked = device.data(device.post(f"/drop/uploads/{upload['id']}/complete"))
    assert device.get(f"/drop/messages/{chunked['id']}/download").content == b"hello"
    assert device.data(device.post(f"/drop/messages/{chunked['id']}/save", json={"destination": "files"}))["saved_to"] == "files"
