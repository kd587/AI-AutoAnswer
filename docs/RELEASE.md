# Release checklist

This checklist applies to a source tag or a Windows binary release. Record results in the release notes; do not turn a simulated test into a claim about a real client.

## Source release

- [ ] Run `npm --prefix AI_AutoAnswer/test_web ci` and `npm --prefix AI_AutoAnswer/test_web test`.
- [ ] On Windows with Python 3.11, run `AI_AutoAnswer/.venv/Scripts/python.exe -m pytest -q` from `AI_AutoAnswer`.
- [ ] Inspect `git diff` and tracked files for API keys, account data, local databases, logs and absolute user paths.
- [ ] Review the exact `@match` and `@connect` entries. The published fixture script must not silently run on unrelated sites.
- [ ] Review README, adapter docs and change notes for accurate tested and untested claims.

## Windows binary release

- [ ] Build on Windows with supported Python 3.11 and 3.13 runtimes using `AI_AutoAnswer/build.bat`. Preserve the whole onedir output.
- [ ] Check license notices for every bundled dependency. Keep the Windows-MCP MIT notice alongside its executable.
- [ ] Start the frozen EXE on a clean Windows 10 and Windows 11 test environment without Python or uv installed.
- [ ] On an interactive desktop, use the local Qt client to verify window picker, screenshot, one single-choice and one multiple-choice click, state verification, next-question change and emergency stop.
- [ ] Run the complete 30-question local fixture and record whether the AI provider was mocked or live.
- [ ] Verify behavior with 100%, 125%, 150% DPI, moved window, target minimized/closed and MCP crash. Mark untested environments explicitly.
- [ ] Sign the distributable if your publisher requires a trusted Windows reputation; do not represent an unsigned build as signed.

Passing CI covers source-level and simulated behavior only. It cannot verify a third-party site's structure, account rules, API answer quality or a frozen EXE on another user's computer.
