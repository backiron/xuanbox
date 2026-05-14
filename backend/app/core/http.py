from urllib.parse import quote


def attachment_headers(filename: str) -> dict[str, str]:
    fallback = "".join(char if 32 <= ord(char) < 127 and char not in {'"', "\\", ";"} else "_" for char in filename).strip()
    fallback = fallback or "download"
    encoded = quote(filename, safe="")
    return {"Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"}
