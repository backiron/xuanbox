import asyncio

RECEIPT_TEXT = """CORNER MARKET
2026-10-05
MILK 2L 5.49
BREAD 3.29
TOTAL 8.78 CAD
"""


def run_worker_until_idle() -> None:
    from app.core.database import engine
    from app.core.redis import redis_client
    from app.workers.ocr_worker import process_once

    async def drain():
        try:
            while await process_once():
                pass
        finally:
            await engine.dispose()
            await redis_client.aclose()

    asyncio.run(drain())


def test_recognised_values_show_before_confirmation(make_user):
    user = make_user("ocr")
    older = user.data(user.post("/receipts/upload", files={"file": ("old.txt", b"OLD SHOP\nTOTAL 1.00", "text/plain")}, data={"purchase_date": "2026-01-01", "merchant": "Typed By Me"}))
    fresh = user.data(user.post("/receipts/upload", files={"file": ("r.txt", RECEIPT_TEXT.encode(), "text/plain")}))
    assert fresh["ocr_status"] == "pending"

    listed = user.data(user.get("/receipts"))
    assert listed[0]["id"] in {fresh["id"], older["id"]} and {item["ocr_status"] for item in listed} == {"pending"}

    run_worker_until_idle()

    receipts = {item["id"]: item for item in user.data(user.get("/receipts"))}
    recognised = receipts[fresh["id"]]
    assert recognised["ocr_status"] == "completed"  # still waiting for the user's review
    assert recognised["merchant"]
    assert recognised["amount"] is not None
    assert recognised["purchase_date"] == "2026-10-05"
    # A value the user typed before recognition is never replaced.
    assert receipts[older["id"]]["merchant"] == "Typed By Me"

    tasks = user.data(user.get(f"/receipts/{fresh['id']}/ocr"))
    confirmed = user.data(user.post(f"/receipts/{fresh['id']}/ocr/{tasks[0]['id']}/confirm", json={"merchant": "Corner Market"}))
    assert confirmed["status"] == "confirmed"
    after = {item["id"]: item for item in user.data(user.get("/receipts"))}[fresh["id"]]
    assert after["merchant"] == "Corner Market" and after["ocr_status"] == "confirmed"
