# XuanBox

A VIANBENI open-source project.

XuanBox is a self-hosted private file vault for personal and small-team use. It provides encrypted file storage, photo management, receipt capture, local document intelligence, controlled sharing, and nearby-device transfer through XuanDrop.

The project is designed for operators who want to run their own private storage service on local hardware or a trusted server. XuanBox is not a hosted cloud service and does not require a third-party account.

## Status

XuanBox is in early preview. Core storage, sharing, user settings, admin controls, OCR, and deployment tooling are available, but operators should review the security model and backup process before using it for important data.

## Features

- Private file storage with encrypted-at-rest blobs.
- Photos, files, receipts, documents, and inbox review flows.
- XuanDrop sessions for nearby-device upload and transfer.
- Public shares with optional password, expiry, and download limits.
- User settings for profile, devices, password, storage, and privacy notes.
- Admin console for users, quotas, registration mode, invites, backups, audit logs, messages, and worker health.
- OCR and document intelligence pipeline for searchable text and document profiles.
- Optional local AI enhancement through an operator-managed Ollama endpoint.
- English and Simplified Chinese interface.

## Security Scope

XuanBox encrypts stored file blobs and isolates user content through product APIs. The current release is not zero-knowledge: the server holds the encryption material required to process files, OCR, previews, and downloads.

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

See [Deployment](docs/DEPLOYMENT.md) for a deployment checklist.

## Optional Local AI

XuanBox can call a local Ollama-compatible endpoint for document and receipt enhancement. AI is optional. Uploads and core storage should work without AI enabled.

When enabled, the worker sends extracted text to the configured endpoint. Do not enable remote AI services for private files unless the deployment owner has reviewed that data flow.

## Licensing

XuanBox is released under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

Commercial licenses are available for organizations that need closed-source integration, managed deployments, hosted services, or support terms outside the AGPL. See [Commercial Licensing](COMMERCIAL.md).

The XuanBox and VIANBENI names, logos, and brand assets are not licensed under the AGPL. See [Trademarks](TRADEMARKS.md).

## Contributing

Contributions are welcome after the project stabilizes. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening issues or pull requests.

## Project

XuanBox is developed and maintained by VIANBENI.

- Website: [vianbeni.ca](https://vianbeni.ca)
- Contact: [xuanbox@vianbeni.ca](mailto:xuanbox@vianbeni.ca)
- Repository: [github.com/backiron/xuanbox](https://github.com/backiron/xuanbox)
