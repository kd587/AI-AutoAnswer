# Contributing

## Scope

Contributions should improve reliability, diagnostics, accessibility, documentation, or adapters for environments that explicitly permit automation. Keep site-specific selectors inside site adapters. Do not add credential harvesting, hidden platform APIs, exam submission, proctoring bypasses, or broad `@match` rules.

## Workflow

1. Open an Issue describing the affected site or desktop client, version, expected behavior, and reproducible steps. Remove names, question contents, account data, and API keys from screenshots or logs.
2. Create a branch and make a focused change. Preserve the existing local fixture adapter as the reference behavior.
3. For browser changes, run `npm --prefix AI_AutoAnswer/test_web ci` and `npm --prefix AI_AutoAnswer/test_web test` from the repository root. Add a test for any new parser or state transition.
4. For desktop changes, use Windows Python 3.11, install `AI_AutoAnswer/requirements.txt`, then run `python -m pytest -q` inside `AI_AutoAnswer`.
5. In the Pull Request, state what was tested with mocks, what was tested on an interactive Windows desktop, and what remains unverified. A green CI result does not prove compatibility with a third-party site.

See [WEB_ADAPTERS.md](docs/WEB_ADAPTERS.md) and [RELEASE.md](docs/RELEASE.md) for extension and release details.
