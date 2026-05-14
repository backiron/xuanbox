# Open Source And Commercial Plan

The purpose of opening XuanBox is trust: privacy software is easier to trust when users can inspect how files, accounts, shares, workers, and admin boundaries work.

## Suggested Split

Community Edition should include:

- Self-hosted user vault.
- Files, photos, receipts, XuanDrop, shares, settings.
- Admin console basics.
- OCR and document intelligence foundation.
- Local AI integration when self-configured.

Commercial features can include:

- Managed deployment support.
- Advanced audit/compliance exports.
- Enterprise backup/retention policies.
- Team policy templates.
- Priority security updates.
- Commercial license for organizations that do not want AGPL-style obligations.

## License Choice

Two reasonable choices:

- AGPLv3 for Community Edition plus separate commercial licenses.
- Source-available self-host license if commercial control is more important than open-source ecosystem compatibility.

Do not call the project enterprise-ready until the threat model, backup guide, audit behavior, and admin-content boundary are documented and tested.

## Product Wording

Use:

- "Encrypted at rest."
- "Admins manage accounts and storage, not private file contents through product APIs."
- "Self-hosted, owner-isolated, inspectable code."

Avoid:

- "Zero knowledge."
- "Impossible for admins to access."
- "Enterprise compliance."
- "Private AI" unless local AI is explicitly enabled and configured by the deployment owner.
