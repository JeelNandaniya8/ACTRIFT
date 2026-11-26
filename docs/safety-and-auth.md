# Safety, authentication and dynamic data

GHOSTDIFF skips common risky English action names by default. Add exact custom labels with `--ignore "Delete, Logout"`. The heuristic is not a security boundary: names may be misleading, localized or unnamed, and GET requests can mutate data. Non-read HTTP methods are blocked unless explicitly enabled. Use disposable local apps, synthetic data and isolated execution only. The explicit `--allow-risky-actions` flag disables the heuristic, not custom ignores.

Use `--mask-text .timestamp --mask-text '#order-id'` for deliberate text exclusions. The selected elements are temporarily hidden during text capture, then restored synchronously; this can affect mutation observers or layout. Action discovery is not masked. Invalid selectors fail rather than silently passing. Exclusions reduce coverage and are recorded in settings.

Use `--screenshots` to include optional viewport images in HTML and JSON evidence. They are not part of the pass/fail signature. Text-mask selectors are also covered in screenshots, but that is not guaranteed sensitive-data redaction.

For authenticated local test apps, create separate Playwright storage-state JSON files using synthetic test accounts and pass `--before-state before.json --after-state after.json`. Never commit state files; they may contain secrets. Use `--storage-state` for verify or recapture, and supply both states for authenticated replay. State filenames and raw cookies/storage are not serialized into reports, but app text, URLs, screenshots and exception messages can still expose data. Do not use real user credentials or production apps. No automatic form filling or submission is implemented.
