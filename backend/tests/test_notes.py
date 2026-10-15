from io import BytesIO

from PIL import Image


def _png(width=40, height=30) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_note_with_text_and_images(make_user):
    me = make_user("note")
    note = me.data(me.post("/notes", json={"body": "Creaksask call\nwords: thoroughly"}))
    image = me.data(me.post(f"/notes/{note['id']}/images", files={"file": ("shot.png", _png(), "image/png")}))
    assert image["marker"] == f"[[img:{image['id']}]]"

    body = f"Creaksask call\n{image['marker']}\nwords: thoroughly, rural"
    saved = me.data(me.patch(f"/notes/{note['id']}", json={"body": body, "base_updated_at": note["updated_at"]}))
    assert saved["body"] == body

    shown = me.get(f"/notes/{note['id']}/images/{image['id']}")
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(shown.content)).size == (40, 30)

    listed = me.data(me.get("/notes", params={"q": "RURAL"}))
    assert [n["id"] for n in listed] == [note["id"]]
    assert listed[0]["title"] == "Creaksask call" and listed[0]["image_count"] == 1
    assert listed[0]["cover_image_id"] == image["id"]
    assert me.data(me.get("/notes", params={"q": "nothing-like-this"})) == []


def test_note_is_private_and_deletes_with_its_images(make_user):
    me, other = make_user("note"), make_user("note")
    note = me.data(me.post("/notes", json={}))
    image = me.data(me.post(f"/notes/{note['id']}/images", files={"file": ("a.png", _png(), "image/png")}))
    assert other.get(f"/notes/{note['id']}").status_code == 404
    assert other.get(f"/notes/{note['id']}/images/{image['id']}").status_code == 404
    assert other.patch(f"/notes/{note['id']}", json={"body": "x"}).status_code == 404
    assert other.data(other.get("/notes")) == []

    # Images must belong to the note they are placed in.
    other_note = other.data(other.post("/notes", json={}))
    assert other.patch(f"/notes/{other_note['id']}", json={"body": image["marker"]}).status_code == 400

    me.data(me.delete(f"/notes/{note['id']}"))
    assert me.get(f"/notes/{note['id']}").status_code == 404
    assert me.get(f"/notes/{note['id']}/images/{image['id']}").status_code == 404


def test_edit_from_another_device_is_not_overwritten(make_user):
    phone = make_user("note")
    laptop = phone.another_device()
    note = phone.data(phone.post("/notes", json={"body": "v1"}))
    laptop.data(laptop.patch(f"/notes/{note['id']}", json={"body": "v2 from laptop", "base_updated_at": note["updated_at"]}))
    stale = phone.patch(f"/notes/{note['id']}", json={"body": "v2 from phone", "base_updated_at": note["updated_at"]})
    assert stale.status_code == 409
    assert phone.data(phone.get(f"/notes/{note['id']}"))["body"] == "v2 from laptop"
    # Pinning does not touch the text and is never a conflict.
    assert phone.data(phone.patch(f"/notes/{note['id']}", json={"pinned": True}))["pinned"] is True
    assert phone.data(phone.get("/notes"))[0]["pinned"] is True


def test_large_photos_are_scaled_and_non_images_refused(make_user):
    me = make_user("note")
    note = me.data(me.post("/notes", json={}))
    big = me.data(me.post(f"/notes/{note['id']}/images", files={"file": ("big.png", _png(4000, 1000), "image/png")}))
    assert (big["width"], big["height"]) == (2560, 640)
    refused = me.post(f"/notes/{note['id']}/images", files={"file": ("x.png", b"not an image", "image/png")})
    assert refused.status_code == 415
