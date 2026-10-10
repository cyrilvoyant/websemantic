# Security policy

WebSemantic is a research prototype. It validates and runs simulation scenarios on the user's machine and runs no
server of its own. Scenarios, parameters and results are written to local folders; the only outgoing requests are
the optional calls to the language-model API that the user configures.

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
