"""Compare an unmodified historical fixed revision with its buggy parent."""
import argparse
import json
from pathlib import Path
from ghostdiff.engine import Settings,compare
from ghostdiff.demo import serve

def run():
    root=Path(__file__).parent/"historical"/"mdn-insert-adjacent"
    good=(root/"fixed.html").read_bytes()
    bad=(root/"buggy.html").read_bytes()
    cfg=Settings(depth=1,budget=8,settle_ms=150)
    with serve(good) as a,serve(bad) as b:
        evidence=compare(a,b,cfg)
    rows={tuple(a["name"] for a in r["path"]):r for r in evidence["paths"]}
    checks=[]
    for label in ("Insert before","Insert after"):
        row=rows.get((label,),{})
        errors=[err for run in row.get("after",[]) for step in run.get("steps",[]) for err in step["outcome"].get("page_errors",[])]
        checks.append({"action":label,"status":row.get("status"),"errors":errors,"passed":row.get("status")=="behavior_changed" and len(errors)>=2})
    return {"kind":"historical upstream example defect","fixed":"07c7d6e7767f272f54be99a49791ab8d61d7af76","buggy":"18cdbb899adfa0d4c8f20c15627a92d0e43dac26","checks":checks,"passed":all(x["passed"] for x in checks),"evidence":evidence}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="historical-benchmark.json")
    a=p.parse_args()
    report=run()
    Path(a.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="evidence"},indent=2))
    raise SystemExit(0 if report["passed"] else 1)
