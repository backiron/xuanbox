# Contributing

Thank you for your interest in XuanBox. The project is still in early preview, so contributions should stay focused, reviewable, and aligned with the current product direction.

## Before Opening A Pull Request

- Check whether the change belongs in the current release scope.
- Keep pull requests small enough to review.
- Avoid unrelated refactors.
- Include screenshots for visible frontend changes.
- Include a short test note for backend, worker, upload, sharing, or security-sensitive changes.

## Development Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Start the local stack:

```bash
docker compose up --build
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend checks:

```bash
cd backend
python -m compileall app
```

Frontend build:

```bash
cd frontend
npm run build
```

## Data And Secrets

Do not commit:

- `.env` files with real values.
- Uploaded files, encrypted storage blobs, thumbnails, previews, or backups.
- Database dumps.
- Logs containing user data, tokens, IP addresses, or private file names.
- Real screenshots of private documents.
- Server passwords, SSH details, API keys, JWT secrets, or master keys.

Use placeholders in documentation and tests.

## Code Style

- Follow existing backend and frontend patterns.
- Prefer clear product language over implementation jargon in user-facing text.
- Keep admin, user, and public-share boundaries explicit.
- Do not weaken access checks for convenience.
- Keep AI features optional and fail-safe; uploads must not depend on AI availability.

## Security-Sensitive Changes

Changes involving authentication, authorization, encryption, shares, backups, admin APIs, or file downloads should include a clear explanation of the threat model and the verification performed.

If you find a vulnerability, do not open a public issue. Follow [SECURITY.md](SECURITY.md).
