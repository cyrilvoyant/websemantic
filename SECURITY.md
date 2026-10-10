# Security policy

WebSemantic is a research prototype. It validates and runs simulation scenarios locally; it does not store user data
and needs no server.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability. Report it privately with GitHub's private vulnerability
reporting: https://github.com/cyrilvoyant/websemantic/security/advisories/new (Security tab, "Report a
vulnerability"). Give the affected version or commit, the steps to reproduce and the expected impact; only the
maintainer sees the report.
Reports are acknowledged within 14 days. A confirmed vulnerability is fixed in a new tagged release, and the release
notes describe it once the fix is public.

## Supported versions

Only the latest tagged release receives fixes.

## Keys and secrets

API keys are read from a local `.env` file, which is never committed. The archive builder (`hpc/build_archive.py`)
refuses to package a file that contains a key.
