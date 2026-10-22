from tests.test_search_ai import make_pro


def test_markdown_is_pro_only(make_user):
    free = make_user("mdfree")
    assert free.post("/files/markdown", json={"name": "plan", "content": "# hi"}).status_code == 403
    uploaded = free.data(free.post("/files/upload", files={"file": ("a.md", b"# old", "text/markdown")}))
    assert free.get(f"/files/{uploaded['id']}/markdown").status_code == 403
    assert free.put(f"/files/{uploaded['id']}/markdown", json={"content": "x"}).status_code == 403


def test_create_edit_and_download_markdown(make_user):
    me = make_user("md")
    make_pro(me)
    created = me.data(me.post("/files/markdown", json={"name": "Trip plan", "content": "# Trip\n\n- passport"}))
    file = created["file"]
    assert file["original_filename"] == "Trip plan.md" and file["mime_type"] == "text/markdown"
    assert file["id"] in [item["id"] for item in me.data(me.get("/files"))]

    saved = me.data(me.put(f"/files/{file['id']}/markdown", json={"content": "# Trip\n\n- passport\n- zanzibarite charger", "base_sha256": file["sha256_hash"]}))
    assert saved["file"]["sha256_hash"] != file["sha256_hash"]
    assert me.data(me.get(f"/files/{file['id']}/markdown"))["content"].endswith("zanzibarite charger")
    download = me.get(f"/files/{file['id']}/download")
    assert download.status_code == 200 and download.content.decode().endswith("zanzibarite charger")

    found = me.data(me.get("/search", params={"q": "zanzibarite"}))
    assert file["id"] in str(found)

    # A second tab still holding the first version must not overwrite the newer save.
    stale = me.put(f"/files/{file['id']}/markdown", json={"content": "old tab", "base_sha256": file["sha256_hash"]})
    assert stale.status_code == 409
    assert me.data(me.get(f"/files/{file['id']}/markdown"))["content"].endswith("zanzibarite charger")


def test_markdown_editing_rules(make_user):
    me, other = make_user("md"), make_user("md")
    make_pro(me)
    make_pro(other)
    created = me.data(me.post("/files/markdown", json={"name": "notes.markdown", "content": ""}))["file"]
    assert created["original_filename"] == "notes.markdown"
    # Uploaded .md files open in the editor too; other file types do not.
    uploaded = me.data(me.post("/files/upload", files={"file": ("readme.md", b"# Readme", "text/markdown")}))
    assert me.data(me.get(f"/files/{uploaded['id']}/markdown"))["content"] == "# Readme"
    text = me.data(me.post("/files/upload", files={"file": ("a.txt", b"plain", "text/plain")}))
    assert me.get(f"/files/{text['id']}/markdown").status_code == 400
    # Never someone else's document.
    assert other.get(f"/files/{created['id']}/markdown").status_code == 404
    assert other.put(f"/files/{created['id']}/markdown", json={"content": "x"}).status_code == 404
    assert me.post("/files/markdown", json={"name": "  ", "content": ""}).status_code == 400
    assert me.put(f"/files/{created['id']}/markdown", json={"content": "a" * (2 * 1024 * 1024 + 1)}).status_code == 413
