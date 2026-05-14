# Roadmap

This roadmap is directional. It is not a release commitment.

## Current Foundation

- User authentication, registration modes, invites, and account settings.
- Separate user app and admin console.
- Files, photos, receipts, documents, inbox review, and XuanDrop.
- Public shares with password, expiry, and download limits.
- Admin users, plans, quotas, messages, audit logs, backups, and worker status.
- OCR, document intelligence tasks, document profiles, and search integration.
- Optional local AI enhancement.
- English and Simplified Chinese interface.

## Near-Term Priorities

- Add focused tests for auth boundaries, quota enforcement, upload flows, public shares, and document intelligence.
- Improve upload review and document classification flows.
- Add direct result links from search into file detail or receipt review panels.
- Add guided backup restore documentation and, later, restore UI.
- Improve audit filtering, pagination, and retention controls.
- Continue mobile layout hardening for narrow screens.

## Document Intelligence

The intended long-term flow is:

```text
Upload original
-> encrypted storage
-> worker extraction
-> document classification
-> structured profile
-> searchable index
-> user review
```

Rules and OCR should remain the baseline. Local AI should remain optional, bounded, and safe to disable.

## Commercial Direction

The community edition should remain useful for self-hosted personal and small-team deployments. Commercial work may focus on managed deployment support, enterprise policy templates, advanced audit exports, backup/retention workflows, and licensing for closed-source or hosted use.
