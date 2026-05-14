# XuanBox Changelog

## 2026-05-07 Hardening

- Replaced the XuanDrop QR placeholder icon with a real scannable QR code generated from the temporary upload URL.
- Added `DROP_PUBLIC_ORIGIN`/`VITE_DROP_PUBLIC_ORIGIN` support so phone QR codes can use a LAN address instead of unusable `localhost`.
- Persisted expiring XuanDrop public tokens so session links and QR codes survive page refresh while the session remains open.
- Added real image OCR support through Tesseract with English and Simplified Chinese language packs in the backend image.
- Added Admin health endpoint at `/api/v1/admin/health`.
- Expanded XuanDrop with realtime server-sent item events, authenticated item download, authenticated item deletion, and frontend live status/download/delete controls.
- Added scheduled backup execution in the worker with `BACKUP_SCHEDULE_HOURS`.
- Added executable restore tooling at `python -m app.scripts.restore_backup <archive> --yes` for backup archive database and encrypted storage recovery.

### Verification

- `python -m compileall backend\app`
- `docker compose run --rm xuanbox-web npm run build`
- `docker compose build xuanbox-api xuanbox-worker`
- Container OCR engine check returned Tesseract `5.5.0`.
- API smoke checks passed for login, `/admin/health`, XuanDrop session creation, public upload, authenticated download, deletion, and realtime event stream.
- Worker started and completed a scheduled backup.

## 2026-05-07

### Step 12: Admin Management

- Added admin API bundle with overview, users, invites, audit logs, backup list, and health-oriented storage stats.
- Added user role/status/quota update endpoint with audit logging and self-disable protection.
- Added aggregate storage and service metrics without exposing private file contents.
- Rebuilt Admin page with overview, users, invites, audit, and backups tabs.

### Step 13: Backup And Migration

- Added backup task database model and Alembic migration `0008_admin_backups`.
- Added manual backup API that writes a local `.tar.gz` archive containing database JSON export, encrypted storage directories, safe config copy, manifest, and restore notes.
- Added backup listing and Admin UI trigger.
- Added safe config export with secrets redacted.
- Marked the blueprint implementation path complete through Step 13.

### Verification

- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m compileall backend/app`
- `docker-compose up -d --build xuanbox-api xuanbox-web xuanbox-worker`
- `docker-compose exec -T xuanbox-api alembic current`
- `docker-compose run xuanbox-web npm run build`
- Admin smoke check: owner loads admin bundle and updates aggregate-only admin data.
- Backup smoke check: manual backup completes and archive is written under `STORAGE_ROOT/backups`.

### Step 11: OCR And Worker

- Added generic `worker_tasks` queue model and `ocr_tasks` OCR result model with Alembic migration `0007_ocr_worker`.
- Added receipt `ocr_status` tracking.
- Added Python async worker entrypoint at `app.workers.ocr_worker`.
- Added `xuanbox-worker` Docker Compose service for background task processing.
- Added receipt OCR task creation, listing, confirmation, and failed-task retry APIs.
- Added lightweight local text extraction and receipt field parsing for text/PDF-like receipt files.
- Added OCR status, trigger, review, confirm, and retry controls to the Receipts workspace.
- Added pending OCR count to Dashboard metrics.

### Verification

- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m compileall backend/app`
- `docker-compose up -d --build xuanbox-api xuanbox-web xuanbox-worker`
- `docker-compose exec -T xuanbox-api alembic current`
- `docker-compose run xuanbox-web npm run build`
- End-to-end OCR smoke check: upload text receipt, trigger OCR, worker completes task, confirm parsed fields, receipt becomes `confirmed`.
- Failed OCR smoke check: upload unsupported image receipt, task becomes `failed`, retry endpoint returns task to `pending`.

### Step 10: Documents And Important Records

- Added document database model, schema, service, API routes, and Alembic migration `0006_documents`.
- Added encrypted document upload linked to file assets.
- Added document metadata for type, title, issuer, issued date, expiry date, note, and security level.
- Added security-level validation for `normal`, `sensitive`, `high_sensitive`, and `vault_locked`.
- Added password re-verification for high-sensitive and vault-locked document downloads as the second-factor placeholder.
- Added document expiry reminder APIs and Dashboard summary metrics.
- Added Documents workspace with upload form, filters, security-level cards, edit modal, and protected download.
- Updated Dashboard to show real storage, file/photo/document counts, and documents expiring in the next 90 days.

### Verification

- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m compileall backend/app`
- `docker compose up -d --build xuanbox-api xuanbox-web`
- `docker compose exec -T xuanbox-api alembic current`
- `docker compose run --rm xuanbox-web npm run build`
- End-to-end API smoke check: sign in with a local test account, upload a high-sensitive document, confirm Dashboard reminder, reject download without password, download with password.

### Step 9: Sharing System

- Added share and share access log database models with Alembic migration `0005_shares`.
- Added authenticated share creation, listing, update, and cancellation APIs.
- Added public share metadata, password verification, and protected download APIs.
- Enforced owner-only share creation, active/expired/download-limit checks, password checks, and cancellation invalidation.
- Added access logs for public share views, password checks, successful downloads, and failed access attempts.
- Added Shared workspace with My shares and Shared with me tabs, link creation, copy link, limits, expiry display, and cancellation.
- Added public share page at `/public-share/:token`.

### Verification

- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m compileall backend/app`
- `docker compose up -d --build xuanbox-api xuanbox-web`
- `docker compose exec -T xuanbox-api alembic current`
- `docker compose run --rm xuanbox-web npm run build`
- End-to-end API smoke check: sign in with a local test account, create a password-protected file share, reject missing password, verify password, download, cancel, confirm public link returns `403`.

### Auth Session Stability Fix

- Added frontend automatic access-token refresh on `401` responses.
- Added original-request replay after a successful refresh.
- Added concurrent request protection so pages loading several protected APIs do not invalidate each other during refresh.
- Cleared local auth state and redirected to login only when refresh fails.
- Fixed mounted-view failures caused by stale access tokens.

### Verification

- `docker compose run --rm xuanbox-web npm run build`
- Manual API refresh smoke check: login, refresh token, then access protected albums endpoint.
- Frontend route checks for `/photos` and `/files`.
- Docker Compose health check for API, PostgreSQL, Redis, and web.

### Step 7: Receipt System

- Added receipt database model, schema, service, API routes, and Alembic migration.
- Added encrypted receipt upload linked to file assets.
- Added structured receipt fields for merchant, category, amount, currency, purchase date, warranty date, and notes.
- Added receipt search and filters for text, category, merchant, and year.
- Completed the Receipts workspace with upload form, metadata form, filter bar, receipt list, and edit modal.

### Step 8: XuanDrop

- Added transfer session and transfer item models, schemas, services, API routes, and Alembic migration.
- Added authenticated PC-side session creation and session/item listing.
- Added public token upload endpoint for mobile or secondary-device uploads.
- Added XuanDrop workspace with session creation, upload link display, refreshable received items, and save actions.
- Added public XuanDrop upload page at `/drop/public/:token`.
- Added save flow for transfer items into Files, Photos, or Receipts.

### Verification

- `python -m compileall backend\app`
- `docker compose run --rm xuanbox-web npm run build`
- `docker compose up -d --build --force-recreate xuanbox-api xuanbox-web`
- Authenticated smoke checks for receipt upload/listing and XuanDrop session/upload/save.
- Frontend route checks for `/receipts` and `/drop`.

### Step 5: File System Completion

- Completed the Files workspace with folder navigation, folder rename, file rename, favorite, move, soft delete, restore, purge, protected download, selection, batch favorite, batch move, and batch delete.
- Added file details drawer with metadata, hash, timestamps, and tag actions.
- Added tag creation, tag attachment, tag link listing, and file tag display.
- Added upload progress feedback for file uploads.
- Fixed root-folder listing semantics so root view only shows root files.
- Hid system-generated photo derivatives from the normal file list.
- Switched downloads to authenticated blob requests so protected files are not fetched through unauthenticated links.

### Step 6: Photo System

- Completed the Photos workspace with multi-photo upload, upload progress, timeline grouping, protected thumbnails, protected previews, and protected original downloads.
- Added large-photo preview with desktop next/previous controls and mobile swipe navigation.
- Added photo favorite support in the UI.
- Added album creation, album listing, add-photo-to-album, and album photo browsing.
- Added backend album photo listing endpoint.

### Verification

- `python -m compileall backend\app`
- `docker compose run --rm xuanbox-web npm run build`
- `docker compose up -d --build --force-recreate xuanbox-api xuanbox-web`
- Authenticated smoke checks for files, tag links, albums, and photos.
