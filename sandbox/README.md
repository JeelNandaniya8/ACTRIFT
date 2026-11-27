# Isolated demo runner

Build the image locally (requires internet during build), then run only the bundled fixture with no container network:

```sh
docker build -f sandbox/Dockerfile -t ghostdiff-preview .
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=512m --tmpfs /home/ghostdiff:rw,nosuid,nodev,uid=10001,gid=10001,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 1g --cpus 2 --shm-size 256m ghostdiff-preview demo --out /tmp/report
```

No host volume or credentials are required. The loopback fixture lives inside the same container. Reports are temporary in this invocation. This is defense in depth, not an audited production sandbox; Playwright's Chromium process sandbox is not explicitly enabled. Do not run hostile applications or mount sensitive host directories. For untrusted workloads use a dedicated disposable VM, restrictive egress and independent security review.

CI also attempts the historical benchmark inside this network-disabled configuration. A passing test establishes that the bundled fixture runs under these restrictions, not that container escapes are impossible.

## Compare two prebuilt static fixtures without host mounts

Use trusted, disposable static directories containing only synthetic assets. The packer accepts regular web assets and rejects hidden paths, symlinks and unsupported extensions. It does not scan file contents for secrets. Do not pack repository roots, source trees or production data.

From the repository (installed locally):

```sh
python -m ghostdiff.static_bundle pack --before ./fixture-v1 --after ./fixture-v2 > bundle.json
docker run --rm -i --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=512m --tmpfs /home/ghostdiff:rw,nosuid,nodev,uid=10001,gid=10001,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 1g --cpus 2 --shm-size 256m --entrypoint python ghostdiff-preview -m ghostdiff.static_bundle compare --allow-actions < bundle.json
```

Both versions are served from bounded in-memory asset dictionaries inside the container; there is no archive extraction, host directory mount, arbitrary build command or external URL input. Only a data-minimized JSON verdict is emitted. Exit 0 means observed agreement, 1 observed differences, 2 inconclusive/error. A 48 MiB input cap, 200 assets per version, 2 MiB per asset and 16 MiB aggregate per version limit the interchange. Use a process timeout as in CI; Docker limits are defense in depth. Running the Python module outside Docker does not provide isolation. Chromium's internal sandbox is not explicitly enabled, and neither this recipe nor its CI test certifies containment of hostile code.
