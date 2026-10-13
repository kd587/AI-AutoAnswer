# Changelog

## Unreleased public foundation

- Added a repository landing page, MIT project license, third-party notices, contribution and security guidance, CI, and a release checklist.
- Kept the Windows desktop client as a separate experimental path and documented its verification boundary.
- Added an explicit browser site-adapter contract to the local Tampermonkey fixture script.
- Added model selection, in-page run events, and redacted CSV export to the fixture script.
- Added a visible userscript-load indicator to the local 30-question test page.
- Added regression tests for invalid AI answers, page changes during an API request, request cancellation, and model configuration.

The browser tests use a mocked API. Real Tampermonkey injection and GitHub-hosted CI remain release checks until observed on the target systems.
