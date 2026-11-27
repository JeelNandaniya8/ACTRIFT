# 0.5.0 research preview

Explicit synthetic form journeys, authenticated local test sessions, risky-action filtering, text masking, screenshot evidence, reviewed rename mappings and contract recapture. The composite GitHub Action exposes numeric summaries and has a clean/broken smoke check. This revision adds action-time HTTP failure evidence and native searchbox support.

Distribution artifacts are gated on CI. This preview is not an audited sandbox, general semantic equivalence checker or guarantee of complete regression detection. Use only disposable local apps and synthetic data. Verify CI for this exact revision before publishing.

Before release, verify all jobs in Tests and review Automated security checks for the exact revision. Include SHA256SUMS with the wheel and source distribution. The new parallel mode is optional; use isolated independent backends. Independent security audit remains outstanding.

A maintainer can manually dispatch the Publish verified preview workflow on main after reviewing security reports. It requires successful push-triggered Tests and Automated security checks for the exact current commit, validates artifact checksums, and refuses to replace an existing release. Repository permissions may still prevent publishing. Do not grant broad access or bypass repository policy.
