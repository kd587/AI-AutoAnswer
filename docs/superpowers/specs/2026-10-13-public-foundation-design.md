# AI AutoAnswer public foundation

## Intent and scope

Make the existing repository understandable, testable, and safe to extend on GitHub. Preserve existing source and uncommitted development work. The browser userscript is the recommended path for web pages; the Windows application remains available as a separate desktop automation path. Neither path claims compatibility with an arbitrary third-party site.

## Deliverables

- A repository-root landing page, permissive project license, third-party notice, contribution and security guidance.
- A documented browser adapter contract with the local 30-question fixture as the reference implementation. URL matching remains explicit and narrow.
- Browser run events visible in the panel and exportable without API keys or question content.
- Windows and Node CI checks for unit and simulated end-to-end tests; packaging is documented separately from tested runtime behavior.
- Release criteria that distinguish deterministic fixture tests, interactive Windows tests, and unverified site compatibility.

## Boundaries

No integration with unselected websites, course progress APIs, protected exam pages, or final submission actions. Do not copy NEUMOOC code or claim its PolyForm Noncommercial license applies to this project. Never put the user's API key in source, logs, fixtures, or commits. Existing Windows MCP and OCR modules remain intact.
