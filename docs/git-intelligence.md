# Local Git intelligence

Use only trusted disposable local Git repositories, with OS/network isolation. The static automation reads exact commit blobs and serves assets on loopback. It never modifies the worktree, checks out a branch, installs dependencies, executes a build script, or contacts a remote.

```sh
actrift git-bisect ./example --good FULL_GOOD_SHA --bad FULL_BAD_SHA --site public --allow-actions --exhaustive
actrift localize report/evidence.json --repo ./example --good FULL_GOOD_SHA --bad FULL_BAD_SHA
```

Good must be within 64 first-parent revisions of bad. A static snapshot must have index.html, up to 200 files, no symlinks/submodules, and bounded asset sizes. The default baseline is captured from the good commit; pass --contracts to protect previously captured observations. Build-dependent or backend applications still require the pre-provisioned revision manifest command. Browser-executed code is untrusted; read-only Git does not enforce browser isolation.

Source localization ranks changed hunks using observed action labels, HTTP paths and runtime source hints when available. It does not prove a file/function caused the bug, resolve source maps, or execute source. The evidence must correspond to the supplied commits; no cryptographic deployment attestation is inferred.

For applications requiring a frontend build, [prebuilt artifact provisioning](build-artifacts.md) accepts reviewed, checksum-bound static outputs instead of executing build scripts.
