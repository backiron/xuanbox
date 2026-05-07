# XuanBox Changelog

## 2026-05-07

### Step 5: File System Completion

- Completed the Files workspace with folder navigation, folder rename, file rename, favorite, move, soft delete, restore, purge, protected download, selection, batch favorite, batch move, and batch delete.
- Added file details drawer with metadata, hash, timestamps, and tag actions.
- Added tag creation, tag attachment, tag link listing, and file tag display.
- Added upload progress feedback for file uploads.
- Fixed root-folder listing semantics so root view only shows root files.
- Hid system-generated photo derivatives from the normal file list.
- Switched downloads to authenticated blob requests so protected files are not fetched through unauthenticated links.

### Step 6: Photo System

- Completed the Photos workspace with multi-photo upload, upload progress, timeline grouping, protected thumbnails, protected previews, and protected original downloads.
- Added large-photo preview with desktop next/previous controls and mobile swipe navigation.
- Added photo favorite support in the UI.
- Added album creation, album listing, add-photo-to-album, and album photo browsing.
- Added backend album photo listing endpoint.

### Verification

- `python -m compileall backend\app`
- `docker compose run --rm xuanbox-web npm run build`
- `docker compose up -d --build --force-recreate xuanbox-api xuanbox-web`
- Authenticated smoke checks for files, tag links, albums, and photos.
