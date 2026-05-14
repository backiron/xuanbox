# Security Policy

XuanBox handles private files and operational metadata. Please report security issues privately.

## Supported Versions

XuanBox is currently in early preview. Security fixes are applied to the main branch until formal release channels are defined.

## Reporting A Vulnerability

Do not publish sensitive vulnerability details in a public issue.

When reporting a vulnerability, include:

- Affected version or commit.
- Steps to reproduce.
- Impact and required permissions.
- Whether user files, credentials, shares, backups, or admin functions are involved.
- Suggested mitigation, if known.

The maintainer will acknowledge valid reports when a private contact channel is available and will coordinate fixes before public disclosure.

## In Scope

- Authentication and session handling.
- User/admin route isolation.
- Unauthorized access to files, receipts, photos, documents, or shares.
- Public share password, expiry, and download-limit bypasses.
- Backup exposure.
- Secret handling.
- Worker processing that leaks private file content.

## Out Of Scope

- Social engineering.
- Vulnerabilities in unsupported third-party deployments.
- Issues caused by exposing an instance without TLS, firewalling, or proper secret management.
- Denial-of-service reports without a clear product-level mitigation.

## Security Model

Read [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) before making claims about privacy or deployment safety.
