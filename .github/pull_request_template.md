## What changed


## Verification

- [ ] Browser fixture tests (`npm --prefix AI_AutoAnswer/test_web test`)
- [ ] Windows Python tests (`python -m pytest -q` in `AI_AutoAnswer`)
- [ ] Interactive browser or desktop test, if this change affects live interaction

State the exact environment and result. Mark checks that were not run as unverified.

## Safety and scope

- [ ] No API key, cookie, account data, private question or raw sensitive log is included.
- [ ] New userscript `@match` and `@connect` rules are limited to the intended target.
- [ ] No final submission action, hidden platform API, or protection bypass was added.
