# GHOSTDIFF

**Git diff tells you what changed in code. Ghostdiff investigates what changed in observable behavior.**

An early research preview of a bounded, model-free browser behavior comparison engine. It discovers accessible buttons and links, replays short journeys in fresh browser contexts, compares text/route changes and downloaded bytes, and emits inspectable evidence. It does not prove correctness or infer whether a change was intended.

## Quick start

Requires Python 3.10+.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m playwright install chromium
ghostdiff demo --out demo-report
```

Open `demo-report/report.html`. The demo contains three **planted** faults: a no-op PDF export, a removed history action, and a theme that fails to persist after reload. `ghostdiff demo --clean` compares a harmless redesign.

```sh
ghostdiff compare --before http://127.0.0.1:3000 --after http://127.0.0.1:3001 --allow-actions --out report
ghostdiff replay report/evidence.json --index 1 --before http://127.0.0.1:3000 --after http://127.0.0.1:3001 --allow-actions
```

Only use disposable local applications with synthetic data. Clicks and GET requests can have side effects. Fresh browser contexts do not reset backend state. The request filter is a precaution, not a security sandbox; isolate test apps and browser at the OS/network level. Reports contain observed page text and download metadata; review before sharing.

## What the preview does (and does not)

- Bounded baseline exploration, exact accessible-name replay, repeated observations, JSON evidence and a standalone HTML report.
- `unmatched` means the original action could not be matched; it could have been renamed. `behavior_changed` and `download_changed` require human review. `inconclusive` is not a pass.
- No arbitrary form filling, authentication, cross-origin workflows, semantic action matching, PDF content validation, or general feature completeness claim. Dynamic text and hidden state may cause false differences or missed behavior. Candidate-only actions are inventoried, not exhaustively explored.
- `--fail-on-change` exits 1 for observed differences, 2 for inconclusive results, otherwise 0. Exploration is capped by depth/budget; untested behavior is not certified.

## Development

```sh
python -m unittest discover -s tests -v
GHOSTDIFF_BROWSER_TESTS=1 python -m unittest discover -s tests -v
```

The browser integration tests exercise planted faults and a clean redesign. Local unit tests are independent of browser availability. Browser execution in the development environment was blocked by policy; CI is intended to validate real navigation on a normal runner. No public benchmark or novelty claim has been established.

License: Apache-2.0.

## Behavioral DNA and regression contracts

Open `demo-report/observatory.html` to inspect the interactive journey tree, or freeze stable baseline observations into executable regression contracts:

```sh
ghostdiff freeze demo-report/evidence.json --out contracts.json --test-out test_protected.py
ghostdiff verify contracts.json --target http://127.0.0.1:3001 --allow-actions
```

See [contract documentation](docs/contracts.md), [benchmark methodology](benchmarks/README.md), and [CI runs](https://github.com/JeelNandaniya8/GHOSTDIFF/actions). The initial browser test workflow passed. The expanded suite must be verified independently. The benchmark is synthetic, not a real-world accuracy claim.

## Release and external benchmark

The research-preview release is gated on passing the expanded CI matrix. See [GitHub Releases](https://github.com/JeelNandaniya8/GHOSTDIFF/releases) for published packages. The external benchmark uses a pinned CC0 MDN dialog example with a deliberately planted fault, not a historical production bug. Run `python benchmarks/upstream.py` to reproduce it.

## Observation reliability

Run `ghostdiff doctor` after installation to verify Chromium launch. The current observation format preserves repeated text occurrences and records action availability changes. A journey with no supported observable effect is classified as `unobserved`, not verified. `--fail-on-change` returns 2 when no equivalent observable journey was found, even if there are no detected changes. Rerun comparison and freeze to migrate older contracts to observation revision 2.

## Browser portability

Chromium is the default. Firefox and WebKit have optional experimental support with a dedicated smoke-test CI gate:

```sh
python -m playwright install firefox
ghostdiff doctor --browser firefox
ghostdiff demo --browser firefox
```

The selected engine is recorded in evidence and retained by replay and frozen contracts. Different engines can expose different behavior; compare using the same engine. This is not a guarantee of macOS Safari equivalence or compatibility with every app.

## Historical evidence, matching and isolated execution

- Run `python benchmarks/historical.py` to compare the original fixed revision of an MDN example with its buggy parent (a documented JavaScript exception).
- Unmatched actions include ranked local name-similarity suggestions; no suggested action is executed automatically. This is a lexical/synonym heuristic, not general semantic equivalence.
- Observation revision 3 records uncaught JavaScript exceptions during actions. Re-run comparison and freeze contracts; earlier formats are rejected.
- See [isolated demo runner](sandbox/README.md). It is not an audited production sandbox.
- Distribution wheels are built as [CI artifacts](https://github.com/JeelNandaniya8/GHOSTDIFF/actions) after the test matrix. Release publishing requires maintainer permissions.
