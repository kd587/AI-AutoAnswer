# Web site adapters

The installable reference script is [`AI_AutoAnswer/test_web/autoanswer.user.js`](../AI_AutoAnswer/test_web/autoanswer.user.js). It only matches the local fixture. Fork the script for one permitted site at a time; do not widen `@match` to every page.

## Contract

Add one object to `ADAPTERS` and an exact host/path `@match`. The core loop calls these methods:

| Method | Required behavior |
| --- | --- |
| `matches(url, doc)` | Return true only for the intended exercise page, after checking both URL and an identifying page element. |
| `readQuestion(doc)` | Return `{stem, type, options, fingerprint}` or `{finished: true}`. `type` is `single` or `multiple`. `options` is a `Map` from visible labels such as `A` to `{input, text}`; `input` is a connected DOM control or option element. |
| `isSelected(option)` | Read the site's current selection state from the real control, such as `checked` or `aria-checked`. |
| `select(option)` | Click the observed control once. Never synthesize coordinates from an AI response. |
| `findNextButton(doc)` | Return the page's current next-question element, or null. |
| `canAdvance(button)` | Confirm the button is present, enabled, visible and means “next question,” not submit. |
| `advance(button)` | Activate only that verified next-question control. |

The loop re-reads the question after the API response, rejects changed questions, validates every returned answer label, checks the full selected set, and waits for a different fingerprint after advancing. Exceptions stop the run and appear in the in-page log. A site adapter must not bypass these checks.

`fingerprint` must change when a new question appears. Use a stable question number plus normalized stem or another observable page identifier. Do not use a fixed delay as proof that a page changed.

## Safe extension sequence

1. Inspect a page that you own or are permitted to automate. Record selectors for the current question, visible choices, real selection controls, next button and completion state.
2. Add the exact `@match` rule and adapter. Keep the fixture adapter intact so its tests remain a regression reference.
3. Add parser tests for single choice, multiple choice, changing option order, loading state, final page and missing controls. Test selection and next-page change with a local DOM fixture.
4. Run `npm --prefix AI_AutoAnswer/test_web test`. Then test manually in Tampermonkey with non-sensitive practice content. Confirm the panel appears, stop works, and the exported log contains no key.
5. Report site version and observed behavior. Do not claim general compatibility from one successful page.

For a framework-rendered page, dispatching a click may update a DOM checkbox without persisting the site's state. Verify the site's own selected state after the event and, where relevant, navigate away and back to check persistence. Do not call undisclosed platform endpoints to force completion.

## AI answer shape

The provider must return exactly:

```json
{"is_question":true,"question_type":"single","answers":["B"],"can_answer":true}
```

The script rejects unknown labels, duplicate answers, extra fields, mismatched question type, and an unreliable answer. The API URL is currently DeepSeek; if adding another provider, keep the same validation boundary and document its network permission in `@connect`.
