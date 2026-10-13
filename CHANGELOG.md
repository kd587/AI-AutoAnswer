# Changelog

## Browser framework updates

- Added a selector-configured adapter for native radio and checkbox pages and a second local DOM fixture.
- Added an in-page diagnostic that reports recognized controls without an API request, plus API timing and run summary logs.
- Added answer evaluation by question type, separately from simulated click and page-turn tests.
- Continued to keep the desktop path experimental; no third-party site compatibility or live-answer accuracy is claimed.

## Unreleased public foundation

- Added a repository landing page, MIT project license, third-party notices, contribution and security guidance, CI, and a release checklist.
- Kept the Windows desktop client as a separate experimental path and documented its verification boundary.
- Added an explicit browser site-adapter contract to the local Tampermonkey fixture script.
- Added model selection, in-page run events, and redacted CSV export to the fixture script.
- Added a visible userscript-load indicator to the local 30-question test page.
- Added regression tests for invalid AI answers, page changes during an API request, request cancellation, and model configuration.

The browser tests use a mocked API. Real Tampermonkey injection and a permitted target site's behavior remain release checks until observed on those systems.
