"""Reproducible regression exercise against a pinned upstream example."""
import argparse
import json
from pathlib import Path
from ghostdiff.demo import serve
from ghostdiff.engine import Settings, compare

def run(executable=None):
    source=(Path(__file__).parent/"upstream"/"mdn-dialog"/"index.html").read_bytes()
    marker=b"dialog.showModal();"
    if source.count(marker)!=1:
        raise ValueError("Upstream fixture changed")
    mutant=source.replace(marker,b"/* planted: dialog does not open */")
    cfg=Settings(depth=1,budget=8,settle_ms=120,executable=executable)
    with serve(source) as a,serve(mutant) as b:
        report=compare(a,b,cfg)
    with serve(source) as a,serve(source) as b:
        clean=compare(a,b,cfg)
    paths={tuple(x["name"] for x in row["path"]):row["status"] for row in report["paths"]}
    observed=paths.get(("Update details",))
    control=clean["summary"]
    passed=observed=="behavior_changed" and control.get("equivalent_observed",0)>0 and set(control)<={"inventory","equivalent_observed","unobserved"} and not report["summary"].get("inconclusive")
    return {"kind":"external open-source example with planted regression","upstream_commit":"1fa1a3babb9075b7c46c8f8eb8addecdf8d9166e","expected":"behavior_changed","actual":observed,"passed":passed,"mutant_summary":report["summary"],"clean_summary":control}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="upstream-benchmark.json")
    p.add_argument("--browser-executable")
    a=p.parse_args()
    result=run(a.browser_executable)
    Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["passed"] else 1)
