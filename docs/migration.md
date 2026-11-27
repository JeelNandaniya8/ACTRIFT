# GHOSTDIFF to ACTRIFT

The former 0.7.0 project shared a name and CLI with an unrelated 2013 image comparison tool. ACTRIFT is our new public brand (action + rift). The previous tag and PyPI distribution remain intact.

| Item | 0.7.0 | 0.8.0 candidate |
| --- | --- | --- |
| Product | GHOSTDIFF | ACTRIFT |
| PyPI distribution | ghostdiff-lab | actrift |
| CLI | ghostdiff | actrift |
| Optional MCP CLI | ghostdiff-mcp | actrift-mcp |
| Editor extension | ghostdiff-evidence | actrift-evidence |
| Python imports | ghostdiff | ghostdiff (compatibility) |
| Saved schemas | ghostdiff.* / v1 | unchanged |
| Existing GHOSTDIFF_* environment options | existing | unchanged |

The new distribution intentionally retains the Python import namespace and evidence formats. Do not co-install ghostdiff-lab and actrift in one environment. Use a fresh virtual environment after the new release is published:

```sh
python -m venv .venv-actrift
source .venv-actrift/bin/activate
python -m pip install actrift==0.8.0
python -m playwright install chromium
actrift doctor
actrift demo --out demo-report
```

Update executable names in existing automation. Keep evidence files and current environment variable names and pin the desired release. Original historical benchmarks and upstream licenses are retained. Repository's old URL remains the canonical legacy path until owner rename; GitHub repository links generally redirect, but GitHub Pages must be redeployed and its new URL checked. Add a new PyPI pending publisher with the final repository name. Do not overwrite the old 0.7.0 tag or files. Domain and trademark clearance are separate tasks; no reservation or legal clearance is implied.
