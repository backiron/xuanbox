# XuanBox

XuanBox is a self-hosted encrypted personal data vault for photos, files, receipts, documents, XuanDrop device transfer, and secure sharing.

This repository is being built from the project blueprint in `xuanbox施工蓝图.md` and `xuanbox设计说明.md`.

## Local Start

```bash
cp .env.example .env
docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

Frontend:

```text
http://localhost:5173
```

Local development storage is mounted at `./data/storage` and should only contain small test files.
