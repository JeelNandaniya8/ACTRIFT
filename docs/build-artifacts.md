# Prebuilt frontend artifact provisioning

Use existing trusted project CI to build each revision of a frontend application (for example, a bundler's static dist output). GHOSTDIFF provisions and compares the resulting static browser assets; it does not execute package installation or repository build scripts.

```sh
ghostdiff artifact-pack ./dist --commit FULL_40_CHARACTER_SHA --out build-a.json
ghostdiff build-bisect manifest.json --allow-actions --exhaustive
```

The first command prints an entry containing commit, artifact filename and sha256. Repeat for each revision, store the JSON artifacts alongside a reviewed manifest, and use entries in chronological revision order:

```json
{"schema":"ghostdiff.build-revisions/v1","revisions":[]}
```

Populate the revisions array with 2–64 real entries from artifact-pack. Each artifact is limited to 24 MiB encoded, 200 regular assets, 2 MiB per asset and 16 MiB decoded. Hidden paths, symlinks and non-web extensions are rejected during packing. The manifest accepts simple adjacent JSON filenames only; checksum and embedded commit label are verified before browser execution and again before provisioning. A mismatch aborts instead of producing a boundary.

By default the first artifact supplies stable baseline contracts. Supply --contracts to use reviewed unauthenticated contracts. Exhaustive mode checks all supplied revisions; binary mode assumes monotonic regression. The tool serves assets in memory and uses disposable loopback origins. This works with static build outputs, not server-rendered apps requiring an active backend or arbitrary build commands. SHA-256 does not prove that an artifact was built from its labeled commit. Trust the producer and use OS isolation with synthetic data; this module is not a sandbox.
