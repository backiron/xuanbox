# Security Model

XuanBox is a self-hosted private file vault. Its security claims are intentionally narrow and operationally realistic.

## Current Guarantees

- File blobs are encrypted at rest before they are written to storage.
- User data is isolated by owner through normal product APIs.
- Admin console APIs manage users, quotas, registration policy, backups, worker status, messages, and audit logs.
- Product admin APIs are not designed to browse or download another user's private file contents.
- Public shares enforce active state, expiry, password checks when configured, and download limits.

## Not Zero-Knowledge

XuanBox is not currently a zero-knowledge system. The server holds the key material required to decrypt files for downloads, previews, OCR, document intelligence, and backups.

A server operator with direct access to the database, storage, environment secrets, or running containers can access sensitive data. Do not describe the current system as impossible for operators to inspect.

## Admin Boundary

Admin accounts are for system operation. They can manage:

- User status, roles, plans, and quotas.
- Registration mode and invites.
- Backup tasks.
- Audit logs and worker health.
- System messages.

Admin accounts should not be used as normal vault accounts. User-facing routes and admin-console routes use separate token context.

## Public Shares

Treat public links as access keys. Anyone with the link, and the password when one is configured, can access the shared item until the link expires, is cancelled or archived, or reaches its download limit.

Use short expiry windows and download limits for sensitive items.

## OCR And Document Intelligence

OCR and document intelligence operate on decrypted file content inside the worker process. This is required to extract text, classify documents, and build search indexes.

Local AI is optional. If enabled, the worker sends extracted text to the configured AI endpoint. Operators should only use an endpoint they control and trust.

## Backups

Backups contain sensitive metadata and encrypted file blobs. Protect backup storage at least as carefully as the live deployment.

A usable restore requires both database metadata and file storage.

## Operational Requirements

Production operators should:

- Use unique, high-entropy `JWT_SECRET_KEY` and `MASTER_KEY` values.
- Keep `.env` files outside public repositories.
- Back up database and storage together.
- Restrict direct access to containers, volumes, and the database.
- Use TLS before exposing XuanBox outside a trusted network.
- Review audit logs after admin, backup, registration, and sharing changes.

## Future Hardening

Stronger privacy claims require additional work such as user-held keys for selected vault areas, signed releases, richer audit coverage, backup restore verification, and a documented incident response process.
