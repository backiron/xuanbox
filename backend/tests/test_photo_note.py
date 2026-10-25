from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.services.note_ai_service import accept_tidy_result
from tests.test_receipt_ocr import run_worker_until_idle

RAW = "13:52\nSalt: 2\nThyme 1.5\nRosemary: 15\nEdit Share"


def _png(lines: list[str]) -> bytes:
    image = Image.new("RGB", (900, 120 + 110 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=72)
    for index, line in enumerate(lines):
        draw.text((60, 60 + 110 * index), line, fill="black", font=font)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_photo_text_becomes_a_note_with_the_photo_attached(make_user):
    me, other = make_user("pnote"), make_user("pnote")
    photo = me.data(me.post("/photos/upload", files={"file": ("recipe.png", _png(["SALT 2", "PEPPER 15"]), "image/png")}))
    task = me.data(me.post(f"/photos/{photo['id']}/note"))
    assert task["status"] == "pending"
    # Asking again while it is queued does not queue a second one.
    assert me.data(me.post(f"/photos/{photo['id']}/note"))["id"] == task["id"]
    assert other.post(f"/photos/{photo['id']}/note").status_code == 404
    assert other.get(f"/photos/note-tasks/{task['id']}").status_code == 404

    run_worker_until_idle()

    done = me.data(me.get(f"/photos/note-tasks/{task['id']}"))
    assert done["status"] == "completed" and done["ai_assisted"] is False
    note = me.data(me.get(f"/notes/{done['note_id']}"))
    assert "SALT" in note["body"].upper() and "15" in note["body"]
    marker = note["body"].strip().splitlines()[-1]
    image_id = marker.removeprefix("[[img:").removesuffix("]]")
    assert me.get(f"/notes/{note['id']}/images/{image_id}").status_code == 200


def test_photo_without_text_fails_without_leaving_a_note(make_user):
    me = make_user("pnote")
    blank = BytesIO()
    Image.new("RGB", (400, 300), (40, 120, 200)).save(blank, format="PNG")
    photo = me.data(me.post("/photos/upload", files={"file": ("sky.png", blank.getvalue(), "image/png")}))
    task = me.data(me.post(f"/photos/{photo['id']}/note"))
    run_worker_until_idle()
    done = me.data(me.get(f"/photos/note-tasks/{task['id']}"))
    assert done["status"] == "failed" and done["error"] == "no_text" and done["note_id"] is None
    assert me.data(me.get("/notes")) == []


def test_tidy_result_is_kept_only_when_it_sticks_to_the_text():
    assert accept_tidy_result(RAW, {"title": "Spices", "body": "Salt: 2\nThyme: 1.5\nRosemary: 15"}) == ("Spices", "Salt: 2\nThyme: 1.5\nRosemary: 15")
    # A list returned as lines is joined.
    assert accept_tidy_result(RAW, {"title": "Spices", "body": ["Salt: 2", "Thyme: 1.5", "Rosemary: 15"]})[1] == "Salt: 2\nThyme: 1.5\nRosemary: 15"
    # A number that was never read is a guess.
    assert accept_tidy_result(RAW, {"title": "Spices", "body": "Salt: 2 g\nThyme: 1.5\nRosemary: 150"}) is None
    # Most of the text gone.
    assert accept_tidy_result(RAW, {"title": "Spices", "body": "Salt"}) is None
    assert accept_tidy_result(RAW, {"title": "x", "body": None}) is None
