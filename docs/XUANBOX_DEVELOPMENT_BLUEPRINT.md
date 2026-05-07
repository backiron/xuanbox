# XuanBox Development Blueprint

The source design documents are:

- `xuanbox设计说明.md`
- `xuanbox施工蓝图.md`

Engineering rules for implementation:

1. Build the security skeleton before business features.
2. Every user resource must be isolated by `owner_id`.
3. Never expose uploaded files through public static paths.
4. Uploaded files are designed for encrypted storage from the first implementation stage.
5. Admin APIs manage the system, not private user content.
6. PC and mobile layouts should be designed together.
7. XuanDrop is a core module.
8. The local path is Docker Compose testing, then repository push, then server deployment.

## Current Implementation Status

- Step 1: Completed.
- Step 2: Completed for local owner bootstrap, login, token handling, invite APIs, and device records.
- Step 3: Completed for encrypted upload, encrypted storage, protected download, listing, and delete flows.
- Step 4: Completed for desktop and mobile shell layouts.
- Step 5: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 6: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 7: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 8: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 9: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 10: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 11: Completed in this pass. See `docs/CHANGELOG.md`.
- Step 12+: Pending.
