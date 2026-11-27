# Safety, authentication and dynamic data

GHOSTDIFF skips common risky English action names by default. Add exact custom labels with `--ignore "Delete, Logout"`. The heuristic is not a security boundary: names may be misleading, localized or unnamed, and GET requests can mutate data. Non-read HTTP methods are blocked unless explicitly enabled. Use disposable local apps, synthetic data and isolated execution only. The explicit `--allow-risky-actions` flag disables the heuristic, not custom ignores.

Use `--mask-text .timestamp --mask-text '#order-id'` for deliberate text exclusions. The selected elements are temporarily hidden during text capture, then restored synchronously; this can affect mutation observers or layout. Action discovery is not masked. Invalid selectors fail rather than silently passing. Exclusions reduce coverage and are recorded in settings.

Use `--screenshots` to include optional viewport images in HTML and JSON evidence. They are not part of the pass/fail signature. Text-mask selectors are also covered in screenshots, but that is not guaranteed sensitive-data redaction.

For authenticated local test apps, create separate Playwright storage-state JSON files using synthetic test accounts and pass `--before-state before.json --after-state after.json`. Never commit state files; they may contain secrets. Use `--storage-state` for verify or recapture, and supply both states for authenticated replay. State filenames and raw cookies/storage are not serialized into reports, but app text, URLs, screenshots and exception messages can still expose data. Do not use real user credentials or production apps. Automatic form discovery or submission is not implemented; explicit synthetic journeys are supported below.

## Explicit forms

```sh
ghostdiff journey examples/search-journey.json --before http://127.0.0.1:3000 --after http://127.0.0.1:3001 --allow-actions
```

Provide named synthetic fill/click/reload steps. Supports accessible textboxes with ordinary text, email, search, URL or telephone inputs; some browser controls require different roles and are not supported. Password-like fields and risky actions are excluded by heuristic. Non-read HTTP methods remain blocked. Storage state is checked against the local origin and cookie host. Never use secrets or personal data in specifications. Rendered input may appear in evidence. Replay using the original specification; discovery contracts cannot freeze scenario evidence.

For a native search input, set `"role": "searchbox"` on the explicit fill step. The default is `textbox`. Both use exact accessible names and the same synthetic-input restrictions.

Explicit journeys support `check` / `uncheck` with a named native checkbox, `select` with a named native single-select and exact option `label`, and `press` with a named textbox/searchbox and `key` restricted to Enter or Escape. Observed checkbox state or select index changes are recorded; rendered values may appear in reports. No arbitrary keys, drag/drop, custom controls or backend writes are enabled. Use synthetic fixtures.
