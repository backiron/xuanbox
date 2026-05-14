# XuanBox 790Pro Deployment Notes

Recommended runtime split:

- API container: FastAPI, auth, metadata APIs.
- Worker container: OCR, document intelligence, backup jobs.
- Postgres: application metadata.
- Redis: worker queue.
- Web container: Vite frontend.
- Ollama: run on the 790Pro host, not inside the XuanBox compose stack.

## Local AI

Keep AI disabled until OCR/search are stable:

```env
DOCUMENT_AI_ENABLED=false
DOCUMENT_AI_BASE_URL=http://host.docker.internal:11434
DOCUMENT_AI_MODEL=qwen2.5:3b
DOCUMENT_AI_TIMEOUT_SECONDS=30
DOCUMENT_AI_MAX_CHARS=6000
DOCUMENT_AI_CONCURRENCY=1
```

When enabling AI, start with a small model and one concurrent task. Uploads should never depend on AI completion; failed AI enhancement falls back to rule-based classification.

## Storage

Set a durable storage root and back it up:

```env
STORAGE_ROOT=/data/xuanbox/storage
MASTER_KEY=replace-with-a-long-secret
JWT_SECRET_KEY=replace-with-a-long-secret
```

Changing `MASTER_KEY` after files exist can make existing encrypted files unreadable unless a migration/re-wrap process is implemented.

## Upgrade Order

1. Stop the web/API/worker containers.
2. Back up Postgres and the storage directory.
3. Pull or build the new version.
4. Run migrations through API startup or `alembic upgrade head`.
5. Start API, worker, and web.
6. Smoke test login, upload, download, share download, search, XuanDrop, settings, and admin console.
