"""Measure planted regression detection and clean control behavior."""
import argparse
import json
from pathlib import Path
from ghostdiff.engine import Settings, compare
from ghostdiff.demo import app, serve

EXPECTED={
    ("Export PDF",):"download_changed",
    ("Search history",):"unmatched",
    ("Toggle theme","Reload page"):"behavior_changed",
}

def run(executable=None):
    cfg=Settings(depth=2,budget=30,settle_ms=150,executable=executable)
    reports={}
    for name,broken in (("planted",True),("clean",False)):
        with serve(app()) as a,serve(app(broken=broken,redesign=True)) as b:
            reports[name]=compare(a,b,cfg)
    observed={tuple(a["name"] for a in r["path"]):r["status"] for r in reports["planted"]["paths"]}
    checks=[{"journey":list(path),"expected":status,"actual":observed.get(path),"passed":observed.get(path)==status} for path,status in EXPECTED.items()]
    control=reports["clean"]["summary"]
    bad=sum(v for k,v in control.items() if k not in ("inventory","equivalent_observed","unobserved","inconclusive"))
    inconclusive=sum(r["summary"].get("inconclusive",0) for r in reports.values())
    result={"kind":"synthetic planted fixtures, not real-world benchmark","checks":checks,"clean_false_differences":bad,"inconclusive_paths":inconclusive,"summaries":{k:v["summary"] for k,v in reports.items()}}
    result["passed"]=all(x["passed"] for x in checks) and bad==0 and inconclusive==0 and control.get("equivalent_observed",0)>0
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="benchmark.json")
    p.add_argument("--browser-executable")
    a=p.parse_args()
    result=run(a.browser_executable)
    Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["passed"] else 1)
