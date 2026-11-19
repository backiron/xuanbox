from io import BytesIO

import httpx
from PIL import Image

from tests.conftest import BASE_URL

PIN = "246810"


def _jpeg(color=(30, 120, 200), size=(640, 480)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _unlock(device, pin=PIN) -> dict:
    status = device.data(device.get("/important-docs/status"))
    path = "/important-docs/unlock" if status["pin_set"] else "/important-docs/setup"
    token = device.data(device.post(path, json={"pin": pin}))["unlock_token"]
    return {"X-Vault-Unlock": token}


def test_upload_straight_into_the_vault_stays_out_of_everything_else(make_user):
    me = make_user("vault")
    unlock = _unlock(me)
    item = me.data(me.post("/important-docs/upload", headers=unlock, files={"file": ("passport-scan.jpg", _jpeg(), "image/jpeg")}))
    assert item["is_image"] and item["title"] == "passport-scan.jpg"

    assert [i["id"] for i in me.data(me.get("/important-docs", headers=unlock))] == [item["id"]]
    assert me.data(me.get("/photos")) == []
    assert all(f["id"] != item["file_id"] for f in me.data(me.get("/files")))
    assert me.data(me.get("/search", params={"q": "passport"}))["results"] == []
    assert me.get(f"/files/{item['file_id']}/download").status_code == 404

    content = me.get(f"/important-docs/{item['id']}/content", headers=unlock)
    assert content.status_code == 200 and content.headers["content-disposition"] == "inline"
    thumb = me.get(f"/important-docs/{item['id']}/thumbnail", headers=unlock)
    assert thumb.status_code == 200 and Image.open(BytesIO(thumb.content)).size[0] <= 480

    # Without the unlock nothing comes out, and another account never sees it.
    assert me.get("/important-docs").status_code == 401
    assert me.get(f"/important-docs/{item['id']}/content").status_code == 401
    other = make_user("vault")
    other_unlock = _unlock(other)
    assert other.get(f"/important-docs/{item['id']}/content", headers=other_unlock).status_code == 404
    assert other.post("/important-docs/upload", headers=unlock, files={"file": ("x.txt", b"x", "text/plain")}).status_code == 401


def test_photo_moved_into_vault_disappears_with_its_previews_and_shares(make_user):
    me = make_user("vault")
    family = make_user("vault")
    photo = me.data(me.post("/photos/upload", files={"file": ("id-card.jpg", _jpeg((200, 40, 40)), "image/jpeg")}))
    public = me.data(me.post("/shares", json={"target_type": "photo", "target_id": photo["id"]}))
    direct = me.data(me.post("/shares", json={"target_type": "photo", "target_id": photo["id"], "shared_with_username": family.username}))
    assert httpx.get(f"{BASE_URL}/public-share/{public['public_token']}/download").status_code == 200

    unlock = _unlock(me)
    item = me.data(me.post(f"/important-docs/from-photo/{photo['id']}", headers=unlock))
    assert item["from_photos"] is True

    assert me.data(me.get("/photos")) == []
    for variant in ("thumbnail", "preview", "original"):
        assert me.get(f"/photos/{photo['id']}/{variant}").status_code == 404
    assert httpx.get(f"{BASE_URL}/public-share/{public['public_token']}/download").status_code in (403, 404, 410)
    assert family.get(f"/shares/received/{direct['id']}/download").status_code in (403, 404, 410)
    assert me.post("/shares", json={"target_type": "photo", "target_id": photo["id"], "shared_with_username": family.username}).status_code == 403
    assert me.post("/shares", json={"target_type": "file", "target_id": item["file_id"]}).status_code == 403

    restored = me.data(me.post(f"/important-docs/{item['id']}/restore", headers=unlock))
    assert restored["destination"] == "photos"
    assert [p["id"] for p in me.data(me.get("/photos"))] == [photo["id"]]
    assert me.get(f"/photos/{photo['id']}/thumbnail").status_code == 200


def test_lock_change_and_forgotten_pin(make_user):
    me = make_user("vault")
    unlock = _unlock(me)
    assert me.get("/important-docs", headers=unlock).status_code == 200

    me.data(me.post("/important-docs/lock"))
    assert me.get("/important-docs", headers=unlock).status_code == 401

    assert me.post("/important-docs/change-pin", json={"current_pin": "000000", "new_pin": "135790"}).status_code == 403
    changed = me.data(me.post("/important-docs/change-pin", json={"current_pin": PIN, "new_pin": "135790"}))
    assert me.get("/important-docs", headers={"X-Vault-Unlock": changed["unlock_token"]}).status_code == 200
    assert me.post("/important-docs/unlock", json={"pin": PIN}).status_code == 403

    assert me.post("/important-docs/reset-pin", json={"password": "wrong-password", "new_pin": "111222"}).status_code == 403
    reset = me.data(me.post("/important-docs/reset-pin", json={"password": me.password, "new_pin": "111222"}))
    assert me.get("/important-docs", headers={"X-Vault-Unlock": reset["unlock_token"]}).status_code == 200
    assert me.post("/important-docs/unlock", json={"pin": "111222"}).status_code == 200


def test_inbox_can_send_to_vault_only_when_unlocked_and_delete_is_final(make_user):
    me = make_user("vault")
    item = me.data(me.post("/inbox/upload", files={"file": ("tax-return.pdf", b"%PDF-1.4 tax", "application/pdf")}))
    assert me.post(f"/inbox/{item['id']}/resolve", json={"action": "vault"}).status_code in (400, 401)
    unlock = _unlock(me)
    resolved = me.data(me.post(f"/inbox/{item['id']}/resolve", headers=unlock, json={"action": "vault"}))
    assert resolved["resolved_as"] == "vault"
    vault_items = me.data(me.get("/important-docs", headers=unlock))
    assert [v["filename"] for v in vault_items] == ["tax-return.pdf"]
    assert all(f["display_name"] != "tax-return.pdf" for f in me.data(me.get("/files")))

    me.data(me.delete(f"/important-docs/{vault_items[0]['id']}", headers=unlock))
    assert me.data(me.get("/important-docs", headers=unlock)) == []
    assert all(f["display_name"] != "tax-return.pdf" for f in me.data(me.get("/trash")))


def test_note_moves_into_the_vault_and_back_unchanged(make_user):
    me, other = make_user("vault"), make_user("vault")
    note = me.data(me.post("/notes", json={"body": "Bank PIN hint: quokkaberry"}))
    image = me.data(me.post(f"/notes/{note['id']}/images", files={"file": ("a.jpg", _jpeg(), "image/jpeg")}))
    body = f"Bank PIN hint: quokkaberry\n{image['marker']}"
    note = me.data(me.patch(f"/notes/{note['id']}", json={"body": body, "pinned": True}))

    # Adding needs an unlocked vault.
    assert me.post(f"/important-docs/from-note/{note['id']}").status_code in (400, 401)
    assert [n["id"] for n in me.data(me.get("/notes"))] == [note["id"]]
    unlock = _unlock(me)
    me.data(me.post(f"/important-docs/from-note/{note['id']}", headers=unlock))

    # Gone from Notes in every way, including its images and search.
    assert me.data(me.get("/notes")) == []
    assert me.data(me.get("/notes", params={"q": "quokkaberry"})) == []
    assert me.get(f"/notes/{note['id']}").status_code == 404
    assert me.get(f"/notes/{note['id']}/images/{image['id']}").status_code == 404
    assert me.patch(f"/notes/{note['id']}", json={"body": "x"}).status_code == 404
    assert me.delete(f"/notes/{note['id']}").status_code == 404

    # Readable in the vault only, and only when unlocked.
    listed = me.data(me.get("/important-docs", headers=unlock))
    assert [(i["kind"], i["id"], i["title"]) for i in listed] == [("note", note["id"], "Bank PIN hint: quokkaberry")]
    assert me.get(f"/important-docs/notes/{note['id']}").status_code in (400, 401)
    assert me.data(me.get(f"/important-docs/notes/{note['id']}", headers=unlock))["body"] == body
    assert me.get(f"/important-docs/notes/{note['id']}/images/{image['id']}", headers=unlock).status_code == 200
    other_unlock = _unlock(other)
    assert other.get(f"/important-docs/notes/{note['id']}", headers=other_unlock).status_code == 404
    assert other.post(f"/important-docs/notes/{note['id']}/restore", headers=other_unlock).status_code == 404

    # Back out: same text, image, pin and edit time.
    assert me.data(me.post(f"/important-docs/notes/{note['id']}/restore", headers=unlock))["destination"] == "notes"
    back = me.data(me.get(f"/notes/{note['id']}"))
    assert (back["body"], back["pinned"], back["updated_at"]) == (body, True, note["updated_at"])
    assert me.get(f"/notes/{note['id']}/images/{image['id']}").status_code == 200
    assert me.data(me.get("/important-docs", headers=unlock)) == []

    # Deleting from the vault is final.
    me.data(me.post(f"/important-docs/from-note/{note['id']}", headers=unlock))
    me.data(me.delete(f"/important-docs/notes/{note['id']}", headers=unlock))
    assert me.get(f"/important-docs/notes/{note['id']}", headers=unlock).status_code == 404
    assert me.get(f"/notes/{note['id']}").status_code == 404


def test_items_return_to_their_folder_and_albums(make_user):
    me = make_user("vault")
    unlock = _unlock(me)

    folder = me.data(me.post("/folders", json={"name": "Contracts"}))
    lease = me.data(me.post("/files/upload", data={"folder_id": folder["id"]}, files={"file": ("lease.pdf", b"%PDF-1.4 lease", "application/pdf")}))
    item = me.data(me.post(f"/important-docs/from-file/{lease['id']}", headers=unlock))
    restored = me.data(me.post(f"/important-docs/{item['id']}/restore", headers=unlock))
    assert (restored["destination"], restored["folder_name"]) == ("files", "Contracts")
    assert [f["id"] for f in me.data(me.get("/files", params={"folder_id": folder["id"]}))] == [lease["id"]]

    # Its folder was deleted while it was in the vault: it comes back to the top of Files, not nowhere.
    item = me.data(me.post(f"/important-docs/from-file/{lease['id']}", headers=unlock))
    me.data(me.delete(f"/folders/{folder['id']}"))
    restored = me.data(me.post(f"/important-docs/{item['id']}/restore", headers=unlock))
    assert restored["folder_name"] is None
    assert lease["id"] in [f["id"] for f in me.data(me.get("/files", params={"root_only": True}))]

    photo = me.data(me.post("/photos/upload", files={"file": ("trip.jpg", _jpeg((10, 200, 90)), "image/jpeg")}))
    album = me.data(me.post("/albums", json={"title": "Trip"}))
    me.data(me.post(f"/albums/{album['id']}/photos/{photo['id']}"))
    item = me.data(me.post(f"/important-docs/from-photo/{photo['id']}", headers=unlock))
    assert me.data(me.get(f"/albums/{album['id']}/photos")) == []
    restored = me.data(me.post(f"/important-docs/{item['id']}/restore", headers=unlock))
    assert (restored["destination"], restored["albums"]) == ("photos", ["Trip"])
    assert [p["id"] for p in me.data(me.get(f"/albums/{album['id']}/photos"))] == [photo["id"]]
    cover = [a for a in me.data(me.get("/albums")) if a["id"] == album["id"]][0]
    assert cover["cover_file_id"] == photo["file_id"]
