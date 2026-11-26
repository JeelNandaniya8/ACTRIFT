# Isolated demo runner

Build the image locally (requires internet during build), then run only the bundled fixture with no container network:

```sh
docker build -f sandbox/Dockerfile -t ghostdiff-preview .
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=512m --tmpfs /home/ghostdiff:rw,nosuid,nodev,uid=10001,gid=10001,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 1g --cpus 2 --shm-size 256m ghostdiff-preview demo --out /tmp/report
```

No host volume or credentials are required. The loopback fixture lives inside the same container. Reports are temporary in this invocation. This is defense in depth, not an audited production sandbox; Playwright's Chromium process sandbox is not explicitly enabled. Do not run hostile applications or mount sensitive host directories. For untrusted workloads use a dedicated disposable VM, restrictive egress and independent security review.

CI also attempts the historical benchmark inside this network-disabled configuration. A passing test establishes that the bundled fixture runs under these restrictions, not that container escapes are impossible.
