"""Measure wall time and exploration limits on synthetic wide pages."""
import argparse
import json
from pathlib import Path
from ghostdiff.demo import serve
from ghostdiff.engine import Settings,compare

def app(n,broken=False):
    buttons="".join(f'<button onclick="document.querySelector(\'p\').textContent=\'{("Wrong" if broken and i==0 else "Result "+str(i))}\'">Action {i:03d}</button>' for i in range(n))
    return ("<!doctype html><html><body>"+buttons+"<p>Ready</p></body></html>").encode()

def cases():
    return [(8,9),(24,13),(64,17)]

def run():
    results=[]
    for width,budget in cases():
        with serve(app(width)) as a,serve(app(width,True)) as b:
            seq=compare(a,b,Settings(depth=1,budget=budget,settle_ms=100))
            par=compare(a,b,Settings(depth=1,budget=budget,settle_ms=100,parallel=True))
        def verdicts(r):
            return [(row["path"],row["status"]) for row in r["paths"]]
        expected=max(0,width-(budget-1))
        same=verdicts(seq)==verdicts(par) and seq["summary"]==par["summary"] and seq["coverage"]==par["coverage"]
        checks=same and seq["summary"].get("behavior_changed")==1 and seq["coverage"]["omitted_budget_branches"]==expected and not seq["summary"].get("inconclusive")
        results.append({"actions":width,"budget":budget,"sequential":seq["performance"],"parallel":par["performance"],"coverage":seq["coverage"],"summary":seq["summary"],"same_verdicts":same,"passed":bool(checks),"observed_speedup":round(seq["performance"]["elapsed_seconds"]/max(par["performance"]["elapsed_seconds"],0.001),3)})
    return {"kind":"synthetic scaling benchmark","results":results,"passed":all(r["passed"] for r in results),"limits":"Wall time varies across runners; no fixed speedup promise. Independent local app origins, one concurrent candidate browser."}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="scale.json");a=p.parse_args()
    data=run();Path(a.out).write_text(json.dumps(data,indent=2),encoding="utf-8");print(json.dumps(data,indent=2))
    raise SystemExit(0 if data["passed"] else 1)
