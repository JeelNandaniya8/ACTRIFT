"""Reproducible large-state validation on the pinned historical TodoMVC application."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from ghostdiff.engine import Action,Settings,replay
from todomvc_history import fixture

def state(url,count):
    tasks=[{"id":i+1,"title":f"Fixture task {i+1:04d}","completed":int(i%2==1)} for i in range(count)]
    return {"cookies":[],"origins":[{"origin":url.rstrip("/"),"localStorage":[{"name":"todos-vanillajs","value":json.dumps({"todos":tasks})}]}]}

def run():
    cases=[]
    cfg=Settings(depth=2,settle_ms=700,timeout_ms=10000)
    with fixture() as good,fixture(True) as bad,fixture() as clean:
        for count in (100,1000):
            for name,path,expected,target in (
                ("historical defect",(Action("link","Active"),Action("button",f"Clear completed ({count//2})")),"behavior_changed",bad),
                ("clean control",(Action("link","Active"),Action("button",f"Clear completed ({count//2})")),"equivalent_observed",clean),
                ("unaffected control",(Action("link","Completed"),Action("link","All")),"equivalent_observed",bad),
            ):
                start=perf_counter()
                result=replay(good,target,path,cfg,state(good,count),state(target,count))
                errors=[err for run in result["after"] for step in run.get("steps",[]) for err in step["outcome"].get("page_errors",[])]
                cases.append({"tasks":count,"case":name,"expected":expected,"observed":result["status"],"elapsed_seconds":round(perf_counter()-start,3),"passed":result["status"]==expected and (name!="historical defect" or len(errors)>=2),"evidence":result})
    return {"kind":"historical reference app large-state validation","cases":cases,"passed":all(c["passed"] for c in cases),"limits":"Synthetic task data in one client-side open-source reference app; not production traffic, a multi-user service, a broad benchmark corpus or a general accuracy estimate."}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="todomvc-scale.json");a=p.parse_args()
    report=run()
    Path(a.out).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({**report,"cases":[{k:v for k,v in c.items() if k!="evidence"} for c in report["cases"]]},indent=2))
    raise SystemExit(0 if report["passed"] else 1)
