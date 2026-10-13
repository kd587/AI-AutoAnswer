# Architecture and extension points

## Browser path

`AI_AutoAnswer/test_web/autoanswer.user.js` contains a small DOM-first engine and an explicit `ADAPTERS` registry. A site adapter observes the current page and performs actions on observed controls. The engine validates AI output, maintains run limits, checks selection state, and waits for a changed question fingerprint. The local fixture in `test_web/` is a deterministic test target; its answers are not available to the userscript at runtime.

This path requires a browser script manager and permission for the matched page plus the configured AI endpoint. It does not need the Windows EXE, Windows-MCP, OCR, or UIA.

## Desktop path

`AI_AutoAnswer/main.py` starts the PySide6 GUI. `app/automation/mcp_runtime.py` and `mcp_client.py` manage a private stdio Windows-MCP server. `window_manager.py` validates the selected HWND/PID and foreground window. `app/core/controller.py` runs the bounded state machine. Recognition prefers accessible controls and falls back to OCR; `app/automation/answer_executor.py` acts only on observed options and verifies selection. `app/ai/deepseek_client.py` handles provider requests; storage keeps configuration and operational events.

The desktop path is useful when there is no accessible browser DOM. It has more environmental failure modes: foreground changes, screenshot permissions, DPI, window movement, OCR quality and control-tree differences. An adapter for a particular client should be isolated, tested on a local fixture first, and allowed to pause when page identity is uncertain.

## Shared principles

- Explicit target selection and narrow matching.
- AI supplies answer labels, never coordinates.
- Stop on ambiguous recognition, invalid answers, failed selection verification or unchanged pages.
- Do not click final submission controls.
- Separate test evidence from compatibility claims.
