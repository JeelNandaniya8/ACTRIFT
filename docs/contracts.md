# Persistent behavioral contracts

Run a comparison against a known-good local baseline, then freeze its repeated, observable journeys:

```sh
ghostdiff freeze demo-report/evidence.json --out contracts.json --test-out test_protected.py
ghostdiff verify contracts.json --target http://127.0.0.1:3001 --allow-actions
```

The generated unittest can run in CI with GHOSTDIFF_TARGET and GHOSTDIFF_CONTRACTS set, and GHOSTDIFF_ALLOW_ACTIONS=1 for disposable authorized targets. Contract verification returns 0 only for observed matches, 1 for changes and 2 for inconclusive observations. No running baseline is needed.

Contracts preserve exact names, text/route deltas and download bytes, not semantic intent. Write-enabled comparisons cannot be frozen; no-op paths without observable outcomes are excluded. Review contracts before committing them because text may include sensitive data.

Observation revision 2 adds repeated-text and action availability evidence. Older evidence and contracts must be recreated before use; they are deliberately rejected rather than silently compared with incompatible observations.
