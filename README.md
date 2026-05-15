# XuanBox

XuanBox is a VIANBENI open-source project for self-hosted private storage.

XuanBox brings files, photos, receipts, documents, sharing, nearby transfer, OCR, and optional local AI into one private workspace. It is designed for people and small teams who want to run their own storage service on local hardware or a trusted server, without depending on a hosted cloud account.

## Project Status

XuanBox is actively developed and ready for self-hosted evaluation and controlled private deployments. The main product flows are implemented, including user accounts, encrypted-at-rest storage, file and photo management, receipt capture, inbox review, sharing, XuanDrop, user settings, admin controls, audit logs, backups, OCR, document intelligence, and deployment tooling.

Before using XuanBox for irreplaceable data, review the security model, configure durable backups, and test recovery in your own environment.

## Features

- Private workspace for files, photos, receipts, and documents.
- Encrypted-at-rest file blobs and account-isolated product APIs.
- Inbox review flow for camera uploads, mobile uploads, and files that need classification.
- XuanDrop sessions for nearby-device upload and transfer.
- Controlled public shares with optional password, expiry time, and download limits.
- Receipt capture, OCR review, searchable text, and document profiles.
- Optional local AI enhancement through an operator-managed Ollama-compatible endpoint.
- User settings for profile, password, devices, storage, appearance, and privacy notes.
- Admin console for users, quotas, registration mode, invites, backups, audit logs, messages, and worker health.
- English and Simplified Chinese interface.

## Security Scope

XuanBox encrypts stored file blobs and isolates user content through product APIs. It is not a zero-knowledge system: the server holds the encryption material required to process files, OCR, previews, and downloads.

Administrators can manage accounts, quotas, registration settings, backups, and system health. Product admin APIs are not intended to browse or download another user's private file contents. Server operators with direct access to the database, storage, secrets, or runtime can still access sensitive data.

See [Security Model](docs/SECURITY_MODEL.md) before deploying XuanBox outside a test environment.

## Quick Start

Requirements:

- Docker and Docker Compose
- Node.js and Python only if running the frontend or backend outside containers

Create a local environment file:

```bash
cp .env.example .env
```

Start the development stack:

```bash
docker compose up --build
```

Open the web app:

```text
http://localhost:5173
```

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

Local development data is stored under `data/`. Do not commit real uploads, backups, logs, database dumps, or production secrets.

## Production Deployment

Use `docker-compose.prod.yml` and `.env.prod.example` as a starting point. Replace every secret, review CORS origins, set durable storage, and configure backups before exposing the service beyond a trusted network.

Uploads are intentionally bounded for small-server deployments: images are limited to 20 MB and other uploaded files are limited to 200 MB. XuanBox is not intended for video libraries or large-file distribution workloads.

See [Deployment](docs/DEPLOYMENT.md) for a deployment checklist.

## Optional Local AI

XuanBox can call a local Ollama-compatible endpoint for document and receipt enhancement. AI is optional; uploads, storage, sharing, OCR, and search work without AI enabled.

When enabled, the worker sends extracted text to the configured endpoint. For private deployments, prefer a local model running on infrastructure controlled by the deployment owner. Do not enable remote AI services for private files unless the owner has reviewed and accepted that data flow.

## Licensing

XuanBox is released under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

Commercial licenses are available for organizations that need closed-source integration, managed deployments, hosted services, or support terms outside the AGPL. See [Commercial Licensing](COMMERCIAL.md).

The XuanBox and VIANBENI names, logos, and brand assets are not licensed under the AGPL. See [Trademarks](TRADEMARKS.md).

## Contributing

Issues, fixes, documentation improvements, and small product refinements are welcome. For larger changes, please open a discussion or issue first so the direction can be agreed before implementation.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening issues or pull requests.

## Project

XuanBox is developed and maintained by VIANBENI.

- Project site: [xuanbox.vianbeni.ca](https://xuanbox.vianbeni.ca)
- Website: [vianbeni.ca](https://vianbeni.ca)
- Contact: [xuanbox@vianbeni.ca](mailto:xuanbox@vianbeni.ca)
- Repository: [github.com/backiron/xuanbox](https://github.com/backiron/xuanbox)
