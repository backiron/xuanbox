# XuanBox Security Model

XuanBox is a self-hosted private file vault. Its near-term security promise is intentionally precise:

- Files are encrypted at rest.
- User data is isolated by owner in normal product APIs.
- Admin console APIs manage users, quotas, backups, workers, invites, and policy. They do not expose another user's private file bytes.
- XuanBox is not yet zero knowledge. The server holds the master key, so a server operator with code/database/storage access can technically decrypt stored files.

## Trust Boundary

User app tokens and admin console tokens are separate. Admin console tokens should not be accepted by user vault APIs, and user app tokens should not access admin APIs.

Admins can see operational metadata such as account status, quota, storage use, worker health, backup status, and audit categories. Admins should not be given product features that browse or download another user's personal files.

## Important Docs

Important Docs adds a short-lived PIN unlock flow on top of normal account login. It is a product-level protection for high-value files. It is not a cryptographic zero-knowledge vault because the backend still performs file access with server-held keys.

## Public Shares

Public links should be treated as keys. Anyone with a valid link, and password when configured, can access the shared target until expiry, archive/cancel, or download limit is reached.

## Document Intelligence And AI

OCR and document intelligence operate on decrypted file contents inside the worker process. By default, local AI is disabled. When `DOCUMENT_AI_ENABLED=true`, the worker sends extracted text, not raw large images, to the configured local Ollama endpoint.

Do not claim AI processing is private unless the endpoint is controlled by the same deployment owner.

## Backups

Backups contain encrypted file blobs and sensitive metadata. They should be stored with the same or stronger protection as the primary deployment.

## Future Hardening

Stronger future claims require client-side encryption or user-held keys for selected vault areas, richer audit coverage, signed releases, and a documented incident/restore process.
