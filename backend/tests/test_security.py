import io
import os
import subprocess
import sys
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from tests.conftest import BASE_URL

OWNER = {"username_or_email": "owner", "password": "owner-password-123"}


def admin_headers(credentials=OWNER) -> dict:
    response = httpx.post(f"{BASE_URL}/auth/admin-login", json=credentials)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def user_id(device) -> str:
    return device.data(device.get("/auth/me"))["id"]


def upload_file(device, content: bytes = b"private family document") -> str:
    return device.data(device.post("/files/upload", files={"file": ("secret.txt", content, "text/plain")}))["id"]


# ---------------------------------------------------------------- sharing


def test_share_for_one_person_is_not_a_public_link(make_user):
    owner, recipient, stranger = make_user("so"), make_user("sr"), make_user("ss")
    file_id = upload_file(owner)
    share = owner.data(owner.post("/shares", json={"target_type": "file", "target_id": file_id, "shared_with_username": recipient.username}))
    assert share["public_token"] is None

    token = None
    for item in owner.data(owner.get("/shares", params={"mode": "created"})):
        assert item["public_token"] is None
    # Even with the internal token, the public endpoints refuse a person-to-person share.
    import psycopg

    from app.core.config import settings

    with psycopg.connect(settings.sync_database_url.replace("postgresql+psycopg", "postgresql")) as connection:
        token = connection.execute("select public_token from shares where id = %s", (share["id"],)).fetchone()[0]
    assert httpx.get(f"{BASE_URL}/public-share/{token}").status_code == 404
    assert httpx.get(f"{BASE_URL}/public-share/{token}/download").status_code == 404

    received = recipient.get(f"/shares/received/{share['id']}/download")
    assert received.status_code == 200 and received.content == b"private family document"
    assert stranger.get(f"/shares/received/{share['id']}/download").status_code == 404
    assert owner.post("/shares", json={"target_type": "file", "target_id": file_id, "shared_with_username": owner.username}).status_code == 400


def test_public_links_always_expire_and_run_out(make_user):
    owner = make_user("pl")
    file_id = upload_file(owner)
    share = owner.data(owner.post("/shares", json={"target_type": "file", "target_id": file_id}))
    assert share["expires_at"] and share["max_downloads"] == 3

    far = (datetime.now(UTC) + timedelta(days=60)).isoformat()
    assert owner.post("/shares", json={"target_type": "file", "target_id": file_id, "expires_at": far}).status_code == 400
    assert owner.post("/shares", json={"target_type": "file", "target_id": file_id, "max_downloads": 500}).status_code == 400
    assert owner.patch(f"/shares/{share['id']}", json={"expires_at": None}).status_code == 400
    assert owner.patch(f"/shares/{share['id']}", json={"max_downloads": None}).status_code == 400
    assert owner.patch(f"/shares/{share['id']}", json={"max_downloads": 10}).status_code == 200


def test_share_password_is_rate_limited_and_never_taken_from_the_url(make_user):
    owner = make_user("pw")
    file_id = upload_file(owner)
    share = owner.data(owner.post("/shares", json={"target_type": "file", "target_id": file_id, "password": "open-sesame"}))
    token = share["public_token"]

    assert httpx.get(f"{BASE_URL}/public-share/{token}/download", params={"password": "open-sesame"}).status_code == 403
    codes = [httpx.post(f"{BASE_URL}/public-share/{token}/verify-password", json={"password": "wrong"}).status_code for _ in range(9)]
    assert codes[:8] == [403] * 8 and codes[8] == 429
    # Locked out even with the right password until the window passes.
    assert httpx.post(f"{BASE_URL}/public-share/{token}/verify-password", json={"password": "open-sesame"}).status_code == 429


# ---------------------------------------------------------------- accounts


def test_login_is_throttled_per_account(make_user):
    device = make_user("lg")
    for _ in range(8):
        assert httpx.post(f"{BASE_URL}/auth/login", json={"username_or_email": device.username, "password": "nope"}).status_code == 401
    blocked = httpx.post(f"{BASE_URL}/auth/login", json={"username_or_email": device.username, "password": device.password})
    assert blocked.status_code == 429


def test_signed_out_access_token_stops_working_immediately(make_user):
    device = make_user("so")
    assert device.get("/auth/me").status_code == 200
    httpx.post(f"{BASE_URL}/auth/logout", headers=device.headers, json={"refresh_token": device.tokens["refresh_token"]}).raise_for_status()
    assert device.get("/auth/me").status_code == 401
    assert device.get("/files").status_code == 401


def test_admins_cannot_take_over_the_owner(make_user):
    owner = admin_headers()
    helper = make_user("adm")
    target = make_user("tgt")
    users = httpx.get(f"{BASE_URL}/admin/users", headers=owner).json()["data"]
    ids = {user["username"]: user["id"] for user in users}
    owner_id = ids["owner"]

    assert httpx.patch(f"{BASE_URL}/admin/users/{ids[helper.username]}", headers=owner, json={"role": "admin"}).status_code == 200
    admin = admin_headers({"username_or_email": helper.username, "password": helper.password})

    assert httpx.patch(f"{BASE_URL}/admin/users/{ids[target.username]}", headers=admin, json={"role": "owner"}).status_code == 403
    assert httpx.patch(f"{BASE_URL}/admin/users/{ids[target.username]}", headers=admin, json={"role": "admin"}).status_code == 403
    assert httpx.patch(f"{BASE_URL}/admin/users/{ids[helper.username]}", headers=admin, json={"role": "owner"}).status_code == 403
    assert httpx.patch(f"{BASE_URL}/admin/users/{owner_id}", headers=admin, json={"status": "disabled"}).status_code == 403
    assert httpx.patch(f"{BASE_URL}/admin/users/{owner_id}", headers=admin, json={"role": "user"}).status_code == 403
    # Admins still manage ordinary accounts.
    assert httpx.patch(f"{BASE_URL}/admin/users/{ids[target.username]}", headers=admin, json={"plan": "pro"}).status_code == 200
    # The owner cannot demote themselves into a system without an owner.
    assert httpx.patch(f"{BASE_URL}/admin/users/{owner_id}", headers=owner, json={"role": "user"}).status_code == 400


def test_forwarded_headers_are_only_trusted_from_a_proxy():
    from app.core.rate_limit import client_ip

    def request(peer, headers):
        return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)

    assert client_ip(request("8.8.8.8", {"x-forwarded-for": "1.2.3.4"})) == "8.8.8.8"
    assert client_ip(request("172.21.0.5", {"x-forwarded-for": "198.51.100.7, 172.21.0.1"})) == "198.51.100.7"
    assert client_ip(request("172.21.0.5", {"cf-connecting-ip": "198.51.100.8", "x-real-ip": "172.20.0.2"})) == "198.51.100.8"


# ---------------------------------------------------------------- receipts


@pytest.mark.parametrize(
    ("text", "purchase", "ai_value", "expected"),
    [
        ("Returns accepted within 90 days", "2026-10-02", "2027-10-02", "2026-12-31"),
        ("Exchange for unworn merchandise: 30 Days", "2026-10-03", None, "2026-11-02"),
        ("LIMITED WARRANTY 2 years parts and labour", "2026-03-15", "2027-03-15", "2028-03-15"),
        ("12 month limited warranty", "2026-01-31", None, "2027-01-31"),
        ("Thank you for shopping", "2026-01-31", "2026-02-28", "2026-02-28"),
    ],
)
def test_warranty_dates_are_computed_in_code(text, purchase, ai_value, expected):
    from app.services.ocr_service import _refine_receipt_fields

    refined = _refine_receipt_fields(text, {"purchase_date": purchase, "warranty_until": ai_value})
    assert refined["warranty_until"] == expected


# ---------------------------------------------------------------- backups (last: restores the database)


def test_backups_are_encrypted_complete_pruned_and_restorable(make_user):
    from app.services.backup_crypto import decrypt_file
    from app.services.backup_service import BACKUP_KEEP, backup_tables

    owner = admin_headers()
    device = make_user("bk")
    upload_file(device, b"backup me please")
    users_before = len(httpx.get(f"{BASE_URL}/admin/users", headers=owner).json()["data"])

    for _ in range(BACKUP_KEEP + 1):
        backup = httpx.post(f"{BASE_URL}/admin/backups", headers=owner, timeout=60).json()["data"]
        assert backup["status"] == "completed", backup
    backups = httpx.get(f"{BASE_URL}/admin/backups", headers=owner).json()["data"]
    completed = [item for item in backups if item["status"] == "completed"]
    assert len(completed) == BACKUP_KEEP
    backup_dir = Path(os.environ["STORAGE_ROOT"]) / "backups"
    files = sorted(backup_dir.glob("*.xbenc"))
    assert len(files) == BACKUP_KEEP

    latest = Path(completed[0]["backup_path"])
    raw = latest.read_bytes()
    assert device.username.encode() not in raw and b"database_export" not in raw

    plain = latest.with_suffix(".check.tar.gz")
    decrypt_file(latest, plain)
    with tarfile.open(plain, "r:gz") as archive:
        names = archive.getnames()
        export = archive.extractfile("database_export.json").read()
    plain.unlink()
    assert "encrypted_files" in names
    for table in ("drop_messages", "inbox_items", "system_settings", "messages", "document_profiles"):
        assert f'"{table}"'.encode() in export, table
    assert set(backup_tables()) >= {"users", "drop_contacts", "document_text_chunks"}

    tampered = latest.with_name("tampered.xbenc")
    data = bytearray(raw)
    data[len(data) // 2] ^= 0xFF
    tampered.write_bytes(bytes(data))
    with pytest.raises(Exception):
        decrypt_file(tampered, latest.with_name("tampered.tar.gz"))
    tampered.unlink()
    latest.with_name("tampered.tar.gz").unlink(missing_ok=True)

    restored = subprocess.run([sys.executable, "-m", "app.scripts.restore_backup", str(latest), "--yes"], capture_output=True, text=True, timeout=120)
    assert restored.returncode == 0, restored.stderr
    users_after = len(httpx.get(f"{BASE_URL}/admin/users", headers=admin_headers()).json()["data"])
    assert users_after == users_before
    device.login()
    files_after = device.data(device.get("/files"))
    assert any(item["original_filename"] == "secret.txt" for item in files_after)
