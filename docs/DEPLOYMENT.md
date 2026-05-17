# Deployment

This guide describes a self-hosted Docker Compose deployment. It is intended for a trusted local network or a server behind a reverse proxy controlled by the operator.

## Components

- `xuanbox-web`: static frontend served by Nginx.
- `xuanbox-api`: FastAPI application and metadata APIs.
- `xuanbox-worker`: OCR, document intelligence, and scheduled work.
- `postgres`: application metadata.
- `redis`: worker queue.
- Optional Ollama endpoint: local AI enhancement.

## Environment

Start from the production example:

```bash
cp .env.prod.example .env
```

Replace every secret:

```env
POSTGRES_PASSWORD=replace-with-a-strong-password
JWT_SECRET_KEY=replace-with-a-long-random-secret
MASTER_KEY=replace-with-a-long-random-secret
```

Set the public origin used for XuanDrop and public links:

```env
DROP_PUBLIC_ORIGIN=http://your-server-ip:15173
CORS_ORIGINS=http://your-server-ip:15173
```

Do not reuse development secrets in production.

## Start

```bash
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

Health check:

```bash
curl http://127.0.0.1:15173/api/v1/health
```

## First Admin Account

Create the first owner/admin account through the bootstrap flow or with the provided script in a controlled shell. Change the password immediately after deployment.

Do not document real production credentials in issues, screenshots, commit messages, or deployment notes.

## Storage

XuanBox stores encrypted file blobs, thumbnails, previews, backups, and metadata. Use durable storage for:

- Postgres data.
- `data/storage`.
- `data/backups`.

Back up both database metadata and storage blobs. A database-only backup is not enough to restore files.

## Local AI

AI is optional. For local AI, run an Ollama-compatible endpoint on the host or another trusted machine.

Recommended starting values:

```env
DOCUMENT_AI_ENABLED=false
DOCUMENT_AI_BASE_URL=http://host.docker.internal:11434
DOCUMENT_AI_MODEL=qwen2.5:3b
DOCUMENT_AI_CONCURRENCY=1
```

Enable AI only after OCR, search, upload, and backup flows are stable.

## Upgrade Checklist

1. Back up Postgres and storage.
2. Pull or build the new version.
3. Review `.env` changes.
4. Start API and worker.
5. Confirm migrations completed.
6. Start web.
7. Smoke test login, upload, download, sharing, search, XuanDrop, settings, backups, and admin console.

## Network Exposure

For internet exposure, place XuanBox behind TLS and a reverse proxy. Review upload limits, CORS, firewall rules, backup location, and domain tunnel behavior before opening public access.
