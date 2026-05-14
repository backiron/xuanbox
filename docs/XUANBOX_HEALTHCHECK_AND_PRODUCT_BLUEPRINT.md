# XuanBox Health Check And Product Blueprint

Date: 2026-05-12

This document is a current-state health check and forward blueprint based on the codebase as it exists now, not only the original construction plan. It is meant to guide the next rounds of product, security, admin, settings, sharing, and document intelligence work.

## 1. Product Direction

XuanBox should be positioned as a self-hosted private file and document vault for families, small teams, and privacy-conscious users.

The product promise should be honest:

- XuanBox encrypts files at rest and prevents normal users and normal admin APIs from browsing another user's private content.
- XuanBox is not yet a zero-knowledge system. The server has the master key and can technically decrypt files through backend code paths.
- The correct near-term claim is "self-hosted, encrypted-at-rest, owner-isolated, admin-content-blind by product policy."
- A future stronger claim would require user-held keys or client-side encryption for selected vault areas.

The open-source reason is sound: privacy tools need inspectable code. Commercial rights can still be preserved by choosing a license and feature split intentionally.

Recommended license strategy:

- Community Edition: AGPLv3 or source-available self-host license.
- Commercial License: paid license for companies that do not want AGPL obligations, managed deployments, or advanced admin/compliance modules.
- Do not promise "enterprise security" until admin separation, audit coverage, backup policy, and threat model docs are complete.

## 2. What Is Already Built

### 2.1 Security And Account Foundation

Implemented:

- JWT access and refresh tokens.
- Login, logout, logout all devices, password change.
- Invite-based user creation.
- Device/session records.
- Role constants: owner, admin, user, guest.
- User statuses: active, disabled, locked, deleted.
- Admin endpoints protected by role checks.

Current gap:

- Admin is still inside the normal user app shell at `/admin`.
- Admin links are visible in desktop sidebar and mobile top menu.
- Admin accounts and normal user accounts are not separated by login surface or token audience.
- There is no route guard preventing an admin account from entering the user vault UI.
- Role is being used for both "system power" and "user tier"; this will become messy.

### 2.2 Encrypted File Layer

Implemented:

- Uploads become encrypted `FileAsset` records.
- Per-file key, AES-GCM encryption, wrapped file key, nonce, auth tag, sha256 hash.
- Owner isolation by `owner_id`.
- Protected download APIs.
- Soft delete, restore, purge.
- Folders, tags, favorites, details.
- Photo derivatives are hidden from normal file listing.
- Vault-locked document files are hidden unless explicitly unlocked.

Current gap:

- Storage quota exists on the `User` model but is not yet enforced consistently as a product policy.
- Search is not backend-indexed.
- There is no unified file lifecycle policy: retention, trash expiration, archive policy, derivative cleanup.

### 2.3 Photos And Albums

Implemented:

- Photo upload, thumbnails, previews, original download.
- Timeline layout and album support.
- Multi-select editing.
- Move to album, delete, share selected photos.
- Mobile layout has been improved, but still needs ongoing polish.

Current gap:

- Multi-photo sharing currently creates normal share setup flow from selected photo IDs, but album/multi-target share semantics are still basic.
- Photo OCR and document classification are not connected.

### 2.4 Receipts And OCR

Implemented:

- Receipt upload and receipt metadata.
- `OcrTask` table for receipt OCR.
- `WorkerTask` queue.
- Worker process for `receipt_ocr`.
- OCR extraction with RapidOCR/Tesseract path, text fallback, and simple PDF text handling.
- Optional Ollama-assisted receipt parse behind receipt-specific settings.

Current gap:

- OCR is still receipt-centered.
- PDF extraction is minimal and should not be treated as a production document pipeline.
- Worker only knows `receipt_ocr`; unknown task types fail.
- AI settings are receipt-specific instead of document-intelligence-level settings.

### 2.5 Documents And Important Docs

Implemented:

- `DocumentAsset` table.
- Document upload and metadata.
- Security levels: normal, sensitive, high_sensitive, vault_locked.
- Important docs PIN support has been added in the current worktree.
- Vault unlock token is short-lived.
- Vault-locked docs are hidden from normal file list and blocked from public share.

Current gap:

- Important docs are a strong start, but the user-facing settings/security explanation is not complete.
- The server-side master key still means this is policy-level separation, not zero-knowledge separation.

### 2.6 XuanDrop

Implemented:

- Temporary drop sessions with QR/link.
- Public token upload from another device.
- Live status and received items.
- Upload progress and mobile upload behavior improved.
- Received files can be saved into Files, Photos, or Receipts.
- Expired sessions are filtered from the active list in the new UI work.

Current gap:

- Transfer lifecycle should be stricter: expire old sessions, clean temporary items, and make completion state clearer.
- PC-to-phone flow is conceptually "upload from this device, open session on phone, download/save there"; it needs clearer copy and possibly a dedicated outbound section.

### 2.7 Sharing

Implemented:

- Public share links and user-targeted shares.
- File/photo/receipt/document/album target types exist in the service boundary.
- Public shares default to 7 days and 3 downloads.
- Password-protected shares now use a short-lived access token after password verification.
- Unicode download filenames fixed.
- Public share blocked for vault-locked docs.
- Share archive support exists in the current worktree through `archived_at`.
- Mobile Shared page has been substantially refactored.

Current gap:

- "Received" is clearer than "Shared with me", but the business meaning should be documented in UI.
- Archive is a soft archive now, but needs a permanent Archive tab on desktop and mobile.
- Album/multi-photo share semantics should be completed.
- Share access logs exist but are not yet surfaced to users.

### 2.8 Admin And Backups

Implemented:

- Admin overview.
- User list and role/status/quota update.
- Invites and audit logs.
- Backup tasks and scheduled backup worker.
- Backup restore script.
- Admin service avoids exposing raw private file content.

Current gap:

- Admin console is not separated from user app.
- Admin capabilities are too small for the target product: no plan management, message center, policy settings, worker/OCR controls, license/commercial settings, or clear system health controls.
- Backup policy needs user-facing warning because backups contain encrypted files plus metadata and are sensitive.

## 3. Main Architectural Decisions

### 3.1 Split User App And Admin Console

This is the next required foundation.

Target behavior:

- Normal user login enters the user app.
- Admin login enters a dedicated admin console.
- User app never shows Admin in sidebar, mobile menu, or search.
- Admin console should have its own route group, layout, topbar, and navigation.
- Admin accounts should not browse personal pages like Photos, Files, Receipts, XuanDrop, Shared, or Settings.
- Owner/admin can manage the system, not inspect user private content.

Implementation shape:

- Add token audience or account scope, such as `aud=user_app` and `aud=admin_console`.
- Add backend dependencies:
  - `require_user_app_account`
  - `require_admin_console_account`
  - `require_storage_owner`
- Add route groups:
  - `/login` for user app.
  - `/admin/login` for admin console.
  - `/admin-console` for admin layout.
- Remove `/admin` from normal app shell.
- Redirect admin accounts away from user app after login.

This separation matters more than making the current Settings page prettier. It defines the product's trust boundary.

### 3.2 Separate Role From Plan

Current role values describe system authority. Paid/free feature access should not be encoded into `role`.

Recommended fields:

- `role`: owner, admin, user, guest.
- `plan`: internal, free, plus, pro, business.
- `storage_limit_bytes`: effective quota, can be derived from plan but overrideable.
- `account_flags`: JSON or explicit booleans for special restrictions.
- `disabled_reason`, `disabled_until`, `terms_accepted_at`, `privacy_accepted_at` if needed later.

Plan controls should include:

- Storage quota.
- Max public shares.
- Max share downloads.
- Max XuanDrop sessions.
- OCR monthly budget or enabled/disabled.
- AI features enabled/disabled.
- Backup visibility or export permissions.

### 3.3 Keep Admin Content-Blind At API Level

Near-term rule:

- Admin can see metadata needed for operations: user, quota, total usage, account status, audit event categories, backup status.
- Admin cannot call APIs that decrypt another user's file bytes.
- Admin cannot browse another user's file list as a user.
- Emergency support access should not exist by default. If ever added, it must require explicit user grant and audit trail.

Important wording:

- Because the server holds `MASTER_KEY`, this is not cryptographic zero knowledge.
- The product should say "admins do not have product access to private file contents" rather than "admins can never access files under any circumstances."

### 3.4 Build Document Intelligence As A Shared Layer

Do not expand receipts as a special island. Add a generic layer:

- `document_intelligence_tasks`
- `document_profiles`
- `document_text_chunks`
- optional `document_field_values`

Recommended task fields:

- `id`
- `owner_id`
- `file_id`
- `source_type`: file, photo, receipt, document, drop
- `status`: pending, processing, completed, failed, confirmed, skipped
- `detected_type`: receipt, invoice, contract, warranty, manual, statement, general, unknown
- `raw_text`
- `parsed_json`
- `confidence`
- `error_message`
- `created_at`, `updated_at`, `finished_at`

Recommended profile fields:

- `file_id`
- `title`
- `summary`
- `document_type`
- `primary_date`
- `amount`
- `currency`
- `issuer`
- `counterparty`
- `warranty_until`
- `serial_number`
- `keywords`
- `labels`
- `confirmed_at`

Recommended text chunk fields:

- `file_id`
- `task_id`
- `page_number`
- `chunk_index`
- `text`
- `tsvector` or a generated search column later.

Pipeline:

```text
Upload original
-> Save encrypted file
-> Create document intelligence task
-> Extract text
-> Classify document type
-> Extract structured fields
-> Build searchable index
-> User confirms or corrects
```

Receipts should migrate gradually:

- Short term: keep receipt OCR unchanged.
- Middle term: create document intelligence tasks for all uploads while receipts still use receipt screens.
- Long term: receipt becomes a specialized view over document profiles where `detected_type = receipt`.

### 3.5 Worker Needs A Dispatcher

The current worker directly checks `task.task_type == receipt_ocr`.

Target:

- Introduce a task handler registry.
- Handlers:
  - `receipt_ocr`
  - `document_extract_text`
  - `document_classify`
  - `document_parse`
  - `document_index`
  - `backup_run`
- Add concurrency limits:
  - OCR: 1-2 concurrent.
  - AI: 1 concurrent.
  - Backup: never overlap.
- Add timeouts and retry policy per task type.
- Failed intelligence tasks must not fail upload.

### 3.6 Backend Search Must Replace Frontend Aggregation

Current `/search` experience loads files/photos/receipts/documents and filters on the client. That will not scale and cannot search OCR content.

Target:

- Add `/api/v1/search`.
- Search files by filename, tags, profile summary, OCR text chunks, receipt fields, document fields.
- Return unified results:
  - type
  - id
  - title
  - subtitle
  - snippet
  - thumbnail if available
  - route/action
- Use Postgres full-text first. Add trigram later if needed.

## 4. Recommended Next Phases

### Phase 0: Stabilize Current Worktree

Goal: make the current feature additions clean and reproducible.

Tasks:

- Confirm all migrations apply from empty database through latest.
- Run frontend build.
- Run backend compile.
- Smoke test login, files, photos, XuanDrop, public share download, important docs PIN, share archive.
- Update changelog for the work after 2026-05-07.

Exit criteria:

- A fresh `docker compose up --build` can boot without manual database repair.
- No public download returns 500 for known valid files.
- No expired XuanDrop session is shown as active.

### Phase 1: User Settings And Admin Split

Goal: establish the correct security boundary before adding more advanced features.

Backend:

- Add account type or token audience for admin console.
- Add admin login endpoint or admin-login mode.
- Add guards so admin APIs require admin-console tokens.
- Add guards so user APIs reject admin-console tokens.
- Add `plan` to users.
- Add effective quota calculation.
- Enforce upload quota in file/photo/receipt/document/drop save paths.

Frontend:

- Remove Admin from normal sidebar and mobile menu.
- Create `/admin/login`.
- Create `/admin-console` layout.
- Build user Settings:
  - profile edit
  - avatar upload
  - password change
  - trusted devices
  - storage usage
  - plan/quota explanation
  - security notice
  - privacy/disclaimer text
- Build admin console:
  - overview
  - users
  - plans/quota
  - invites
  - messages
  - audit
  - backups
  - worker/OCR settings

Exit criteria:

- A normal user cannot see or route into admin UI.
- An admin console token cannot browse normal user vault pages.
- Quota is actually enforced during uploads.

### Phase 2: Document Intelligence Foundation Without AI

Goal: build the generic OCR/searchable text layer without adding model complexity yet.

Backend:

- Add `document_intelligence_tasks`.
- Add `document_profiles`.
- Add `document_text_chunks`.
- Add task creation after file/photo/document/receipt upload.
- Add worker handlers for image OCR and simple PDF text extraction.
- Store raw text and chunks.
- Add retry endpoint.

Frontend:

- Add Intelligence section on file/document/photo detail.
- Show status: pending, processing, completed, failed.
- Show extracted text.
- Add retry button.

Exit criteria:

- Uploading an image or PDF creates a generic intelligence task.
- Worker extracts text into the new tables.
- User can see extracted text from the item detail page.

### Phase 3: Full-Text Search

Goal: make OCR immediately useful.

Backend:

- Add `/api/v1/search`.
- Search filenames, receipt metadata, document metadata, OCR chunks.
- Return snippets and result type.

Frontend:

- Replace client aggregation in SearchView with backend search.
- Add filters for Files, Photos, Receipts, Documents.

Exit criteria:

- Searching a word that only appears inside an uploaded image/PDF finds the file.

### Phase 4: Classification And Structured Profiles

Goal: turn OCR text into useful records.

Backend:

- Add rule-based classifiers:
  - receipt
  - invoice
  - warranty
  - contract
  - manual
  - statement
  - general
- Add extractor modules per type.
- Generate document profiles.
- Let receipt page read from both old receipt fields and new profile fields during migration.

Frontend:

- Intelligence section shows document type, summary, extracted fields.
- User can confirm/correct fields.

Exit criteria:

- Receipts, invoices, warranty cards, and general documents classify correctly for common samples.

### Phase 5: Local AI Enhancement

Goal: improve classification, summaries, and fields with bounded 790Pro load.

Backend:

- Replace receipt-specific AI settings with document AI settings:
  - `DOCUMENT_AI_ENABLED`
  - `DOCUMENT_AI_BASE_URL`
  - `DOCUMENT_AI_MODEL`
  - `DOCUMENT_AI_TIMEOUT_SECONDS`
  - `DOCUMENT_AI_MAX_CHARS`
  - `DOCUMENT_AI_CONCURRENCY`
- Use AI only after text extraction.
- Do not send raw large images to the model.
- Truncate and chunk long text.
- Add fallback to rules when AI fails.

Deployment:

- Keep Ollama on the 790Pro host.
- API/Worker/Postgres/Redis stay in Docker Compose.
- Worker calls `host.docker.internal:11434`.
- Default AI off.

Exit criteria:

- AI can summarize and classify selected completed OCR tasks without blocking uploads.

### Phase 6: Open-Source And Commercial Readiness

Goal: make the repository credible for privacy-sensitive users and commercially usable.

Docs:

- Threat model.
- Security model.
- Admin-content-boundary explanation.
- Backup and restore guide.
- Deployment guide for 790Pro.
- License explanation.
- Privacy and disclaimer templates.

Product:

- Admin console polished.
- User settings complete.
- Logs/audit visible where appropriate.
- Public share behavior documented.
- Versioned migrations stable.

Exit criteria:

- A privacy-conscious user can inspect the repo and understand exactly what XuanBox protects, what it does not protect, and how to deploy it safely.

## 5. Immediate Recommendation

Do not start with AI yet.

The next development sprint should be:

1. Stabilize the current worktree and migrations.
2. Split admin console from user app.
3. Build user Settings properly.
4. Add plan/quota fields and enforce quota.
5. Then start generic Document Intelligence tables and worker dispatcher.

Reason:

- Admin separation is a trust boundary.
- Settings is where users learn what is safe, what they control, and what their limits are.
- Plan/quota must exist before commercial packaging.
- Document Intelligence will touch uploads, workers, search, file detail, and receipts, so it should be added after the account model is cleaner.

## 6. Concrete Next Sprint Backlog

### Sprint A: Trust Boundary

- Add `plan` column to users.
- Add admin-console token audience.
- Add user-app token audience.
- Move `/admin` to `/admin-console`.
- Hide Admin from user shell.
- Add route guards.
- Add tests/smoke checks for user/admin route isolation.

### Sprint B: Settings

- Add profile update API.
- Add avatar upload API using existing encrypted file layer.
- Add storage usage endpoint.
- Add settings page sections:
  - Profile
  - Security
  - Devices
  - Storage
  - Legal and privacy notes
- Keep copy clear and non-alarmist.

### Sprint C: Admin Console

- New admin layout.
- Users table with role, plan, status, quota.
- User disable/enable.
- Storage summary.
- Messages/announcements table design.
- Worker/OCR toggles display.

### Sprint D: Document Intelligence Base

- Add new tables and schemas.
- Add worker dispatcher.
- Create OCR tasks on upload.
- Extract text for images and PDFs.
- Add item detail intelligence panel.

## 7. Product Copy Principles

Use simple, honest wording:

- "Encrypted at rest" instead of "impossible to access."
- "Admins manage accounts and storage, not your private files."
- "Your server owner controls the deployment and backup location."
- "Important files can require a PIN before opening."
- "Public links should be treated like keys: anyone with the link and password can access them until they expire."

Avoid overclaiming:

- Do not claim zero knowledge yet.
- Do not claim enterprise compliance yet.
- Do not claim AI is private unless local AI is enabled and clearly configured.

## 8. Final Product Shape

XuanBox should become three connected products:

- User Vault: files, photos, receipts, documents, search, XuanDrop, shares, settings.
- Admin Console: users, plans, quotas, invites, messages, audit, backups, workers, deployment health.
- Intelligence Layer: OCR, classification, summaries, structured fields, full-text search.

The correct order is trust boundary first, intelligence second, commercial packaging third.
