# Evidence intelligence (experimental)

- `ghostdiff fingerprint report/evidence.json --side before --out fingerprint.json`: hashes repeatable observable deltas; compare scope hashes first. No secret-redaction guarantee.
- Capture forward and reverse comparisons using identical settings and swapped local URLs, then `ghostdiff match forward/evidence.json reverse/evidence.json`. Same-role one-step outcomes are compared and ambiguous candidates retained. This is conservative observational matching, not general language understanding. Review manually and use the existing explicit alias format.
- `ghostdiff diagnose report/evidence.json`: first repeatable differing step, HTTP paths, exception messages and download evidence. No automatic source-code attribution.
- `ghostdiff bisect examples/revisions.json contracts.json --allow-actions --exhaustive`: provision independent local revisions yourself and substitute actual full commit SHAs and URLs. Binary mode is faster but assumes monotonic regression; exhaustive mode can detect non-monotonic behavior in the supplied list. The command does not run build scripts, checkout repositories, or certify deployed SHA identity. Use disposable synthetic apps only.

Each output is versioned JSON and can be saved with --out. Do not share raw evidence without review.
