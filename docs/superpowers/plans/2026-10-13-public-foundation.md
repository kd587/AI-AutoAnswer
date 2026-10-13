# Public Foundation Implementation Plan

> **For agentic workers:** Implement task by task in the existing checkout. Preserve pre-existing uncommitted changes.

**Goal:** Publishable source foundation with honest compatibility claims and a documented extension path.

**Architecture:** The repository root is the public project entry point. The current Python desktop application remains in `AI_AutoAnswer/`; its local web fixture userscript demonstrates a DOM adapter and a bounded automation loop. CI validates both code paths without claiming live third-party integration.

**Tech Stack:** Python 3.11, PySide6, Node.js 20, Tampermonkey JavaScript, pytest, node:test, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-13-public-foundation-design.md`

## Tasks

1. Add repository metadata: root README, MIT project license, third-party notice, contribution and security guidance.
2. Add a clear web adapter extension point and bounded in-panel run log. Write failing Node tests first, implement, then rerun the browser fixture suite.
3. Add GitHub Actions CI for Windows Python tests and Node fixture tests. Document release gates and run both local suites.
4. Inspect the resulting diff for secret leakage, unintended third-party code, and claims unsupported by test evidence.
