# Explicit API observation

Use `--observe-api /api/items` on disposable local apps containing synthetic data only. Up to 20 exact paths are selected; only same-origin fetch/XHR responses triggered during an action are sampled. No direct probing, arbitrary URLs or new browser write permissions. Status, method, path and canonical JSON SHA-256 are retained, not query strings, headers or raw body. A selected response must be JSON with a declared uncompressed size no greater than 64 KiB (204/304 are status-only). Invalid, oversized or unsupported selected responses make the journey inconclusive.

This is bounded post-response inspection, not a network quota. Browser transfers may consume resources before checks and response retrieval can wait for a stalled response; use OS-level process/network limits. Hashes can expose low-entropy values through guessing, and paths/rendered content may contain sensitive data. JSON array ordering matters. Initial-load API responses and responses outside the action observation window are not compared. Do not treat digest equality as semantic equality.

The selected path list is part of contract settings and fingerprint scope. The default remains no API body inspection.

Only completed selected requests are inspected. A selected request that fails, exceeds the event budget or remains unfinished at the end of the observation window makes the journey inconclusive instead of waiting for its body. Initial-load selected requests must finish before action observation starts; their contents are not compared. This remains bounded timing-based observation, not a complete network trace.
