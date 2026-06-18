# Security Policy

## Supported Versions

Security fixes are prioritized for the default branch. If release branches or tags are introduced later, this policy should be updated with the supported versions.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Report security concerns privately to the maintainers with:

- A description of the issue and potential impact.
- Steps to reproduce or a proof of concept, when safe to share.
- Affected versions, commits, components, or deployment modes.
- Any known mitigations.

Maintainers should acknowledge the report as soon as practical, investigate the issue, and coordinate a fix before public disclosure.

## Security Expectations

- Do not commit secrets, tokens, private keys, database dumps, or production `.env` files.
- Rotate credentials immediately if they may have been exposed.
- Prefer least-privilege credentials for local development, CI, and deployments.
- Keep dependencies updated and review security advisories regularly.
