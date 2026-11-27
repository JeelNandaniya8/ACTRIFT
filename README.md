# GHOSTDIFF

**Git diff shows what changed in code. GHOSTDIFF investigates what changed in observable behavior.**

A local-first research preview for comparing two disposable web application versions, replaying user journeys, and preserving stable regression contracts. No required external model API. Not a general proof of software correctness.

## Quick start

Python 3.10+ and a Playwright browser are required.

```sh
git clone https://github.com/JeelNandaniya8/GHOSTDIFF.git
cd GHOSTDIFF
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m playwright install chromium
ghostdiff doctor
ghostdiff demo --out demo-report
```

Open `demo-report/report.html` or `demo-report/observatory.html`. The demo has three deliberately planted regressions: a PDF export no-op, missing history button, and theme persistence failure. Use `ghostdiff demo --clean` for a harmless redesign control.

## Compare and preserve

```sh
ghostdiff compare --before http://127.0.0.1:3000 --after http://127.0.0.1:3001 --allow-actions --out report
ghostdiff freeze report/evidence.json --out contracts.json
ghostdiff verify contracts.json --target http://127.0.0.1:3001 --allow-actions
ghostdiff fingerprint report/evidence.json --side before
ghostdiff diagnose report/evidence.json
```

Use `ghostdiff match` on forward/reverse captures for review-only rename hypotheses, and `ghostdiff bisect` for a supplied ordered manifest of already-running local revisions. See [evidence intelligence](docs/intelligence.md). These are constrained observational tools, not general semantic inference, automatic build orchestration, or source-level root cause proof.

## Features and limits

- Bounded baseline action discovery, repeated observations, download hashing, JavaScript and HTTP failure evidence, HTML/JSON reports.
- Chromium default; Firefox and WebKit smoke coverage. Optional parallel comparison of independent local app versions.
- Stable regression contracts, explicit reviewed aliases, legacy recapture, and synthetic form journeys with local test-account storage state.
- Optional text masks, screenshots, action ignore rules, strict coverage gate and [reusable GitHub Action](docs/github-action.md).
- `--fail-on-change` rejects observed differences and inconclusive results; `--require-complete` also rejects skipped, unobserved and budget-omitted paths within the chosen depth.
- Candidate-only actions are inventoried, not exhaustively explored. Unmatched can mean rename; dynamic state can cause false differences; GET can mutate data.

**Safety:** Use only disposable local applications and synthetic data. Fresh browser contexts do not reset backend state. Request filtering is not a security sandbox. Raw evidence may contain sensitive data. See [SECURITY](SECURITY.md), [safety and authentication](docs/safety-and-auth.md), and [isolated demo runner](sandbox/README.md). Independent security audit remains open.

## Evidence and benchmarks

[GHOSTBENCH methodology](benchmarks/README.md) separates planted faults, upstream historical defects, clean controls and bounded scaling. The previous verified 0.5.0 revision (29d21e5) passed all eight CI jobs, including six TodoMVC large-state cases. See [exact CI evidence](https://github.com/JeelNandaniya8/GHOSTDIFF/actions/runs/45943920394) and [security scans](https://github.com/JeelNandaniya8/GHOSTDIFF/actions/runs/45943920498). New revisions require fresh verification. No broad accuracy or production-scale certification is claimed.

## Development and release

```sh
python -m unittest discover -s tests -v
GHOSTDIFF_BROWSER_TESTS=1 python -m unittest discover -s tests -v
```

[CI results](https://github.com/JeelNandaniya8/GHOSTDIFF/actions) · [Contract docs](docs/contracts.md) · [Roadmap](docs/roadmap.md) · [Launch kit](docs/launch.md)

Distribution artifacts are gated on CI. A maintainer can dispatch the verified-release workflow only after reviewing the exact revision's successful test/security runs. The project is an experimental preview; official publication and independent review are separate milestones.

Apache-2.0. Vendored benchmark sources retain their upstream licenses.

New experimental commands: `ghostdiff git-bisect` provisions trusted local static Git snapshots automatically without modifying the checkout; `ghostdiff localize` ranks changed source hunks against observed error paths and action labels. [Git intelligence usage](docs/git-intelligence.md). Matching now examines stable shared-prefix contexts as well as initial actions.

Use `ghostdiff compare-config examples/compare.json --allow-actions` with reviewed local URLs for repeatable configuration and optional reverse (candidate-side) exploration. Explicit journeys support native checkbox, single-select and Enter/Escape actions. macOS and Windows Chromium smoke checks are included in CI. These are not full platform or arbitrary interaction coverage.

For stateful disposable local fixtures, explicitly enable the [backend reset protocol](docs/backend-reset.md) with `--reset-backend`. It requires a dedicated fixture-only endpoint and independent servers, and is not a general database reset mechanism.

Explicit JSON API comparison: `--observe-api /api/items` records bounded response status and digest evidence for selected local synthetic endpoints. See [API observation](docs/api-observation.md). `ghostdiff timeline examples/timeline.json` combines saved fingerprints across operator-supplied revisions; different scopes are marked incomparable.

The portable Observatory includes status filters, journey search and coverage/performance summaries. Comparisons also save `diagnostics.json` for first-divergence inspection. Selected API requests must complete within the observation window or the result is inconclusive.
