# XuanBox Roadmap

## Completed Foundation

- Admin and user app separation.
- User settings: profile, avatar, password, devices, storage, notes.
- Admin console: users, plans, messages, audit, backups, worker health.
- XuanDrop cleanup and mobile improvements.
- Sharing defaults, archive flow, password gate, mobile layout.
- Document Intelligence tables, worker extraction, file detail panel.
- Unified backend search across filenames, metadata, profiles, fields, and OCR text.

## Current Intelligence Layer

Upload flow:

```text
Upload original -> encrypted file -> worker task -> text extraction -> rule classification -> profile + fields -> searchable index -> user confirmation
```

Optional AI flow:

```text
Extracted text -> local Ollama enhancement -> merged profile -> fallback to rules if AI fails
```

## Next Product Hardening

- Add targeted tests for route isolation, share downloads, quota enforcement, and intelligence profile edits.
- Add result deep links so search opens a file detail drawer directly.
- Improve OCR for scanned PDFs with page-level chunks.
- Add audit entries for profile confirmation, share archive, and admin policy changes.
- Add backup restore UI or guided admin workflow.
- Decide final Community/Commercial license.
