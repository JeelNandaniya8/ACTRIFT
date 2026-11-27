# Explicit backend reset protocol

For independently disposable synthetic test servers only. A fresh browser context does not reset server databases. Implement a dedicated POST /_ghostdiff/reset handler that atomically restores your test fixture to a known state and returns 204 only after completion.

```sh
actrift compare --before http://127.0.0.1:3000 --after http://127.0.0.1:3001 --allow-actions --reset-backend --fail-on-change
```

The flag separately authorizes the reset operation. Actrift sends an empty direct HTTP POST to the fixed reset endpoint on the exact numeric loopback host and port before every observation, including initial inventory. No redirects, credentials or arbitrary commands. A failed reset is inconclusive. The feature requires distinct servers, sequential execution and the normal read-policy browser actions; GET can still mutate state. Both servers must have independent test data. A 204 receipt does not establish that the server really reset the correct database. Do not expose this handler in production or test real accounts.

Reset-dependent reports record their policy and cannot yet be frozen or replayed as normal contracts. Fingerprint scope includes reset status. The integration test uses a real in-memory SQLite database behind each local HTTP server to demonstrate drift without resets, stable agreement after resets, and detection of a changed increment. This is a synthetic stateful backend, not production validation.
