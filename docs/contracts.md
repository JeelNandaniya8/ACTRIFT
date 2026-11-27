# Persistent behavioral contracts

Run a comparison against a known-good local baseline, then freeze its repeated, observable journeys:

```sh
ghostdiff freeze demo-report/evidence.json --out contracts.json --test-out test_protected.py
ghostdiff verify contracts.json --target http://127.0.0.1:3001 --allow-actions
```

The generated unittest can run in CI with GHOSTDIFF_TARGET and GHOSTDIFF_CONTRACTS set, and GHOSTDIFF_ALLOW_ACTIONS=1 for disposable authorized targets. Contract verification returns 0 only for observed matches, 1 for changes and 2 for inconclusive observations. No running baseline is needed.

Contracts preserve exact names, text/route deltas and download bytes, not semantic intent. Write-enabled comparisons cannot be frozen; no-op paths without observable outcomes are excluded. Review contracts before committing them because text may include sensitive data.

Observation revision 2 adds repeated-text and action availability evidence. Older evidence and contracts must be recreated before use; they are deliberately rejected rather than silently compared with incompatible observations.

Revision 3 adds action-time uncaught exception evidence. Rerun compare and freeze to migrate; baseline journeys containing exceptions are not frozen as healthy contracts. No unsafe automatic migration of older evidence is attempted.

## Recapture older contracts

```sh
ghostdiff recapture old-contracts.json --baseline http://127.0.0.1:3000 --out contracts-v3.json --allow-actions
```

Use a known-good disposable baseline, never the new unverified candidate. Every previous observable field must match in repeated runs, and every prior contract must be recaptured; otherwise the command refuses. It never overwrites an existing destination. Inspect the output before adoption.

## Explicit action aliases

For a reviewed rename, provide a JSON file:

```json
{"schema":"ghostdiff.aliases/v1","aliases":[{"contract_id":"actual-contract-id","step":0,"from":"Export PDF","to":"Download PDF"}]}
```

Pass it to `ghostdiff verify contracts-v3.json --target http://127.0.0.1:3001 --allow-actions --aliases aliases.json`. The exact replacement action is clicked only when the developer explicitly provides the mapping. Outcome assertions are unchanged, and evidence records the executed path. This does not prove semantic equivalence; it simply allows reviewed renames to be tested.

Healthy older revision-3 contracts remain readable. New action-time HTTP failure evidence is optional when no failures occur; a baseline with observed HTTP failures cannot be frozen or recaptured as healthy. Older contracts do not prove those failures were absent when originally captured.
