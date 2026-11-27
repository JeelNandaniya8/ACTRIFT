"""Pinned historical htmx invalid target fallback, plus a clean control."""
import argparse
import json
from pathlib import Path
from htmx_history import fixture
from ghostdiff.engine import Action,Settings,replay

ROOT=Path(__file__).parent/"historical"/"htmx_ajax"
HTML=b"""<!doctype html><html><head><script src="/htmx.js"></script></head><body><button onclick="htmx.ajax('GET','/test','#missing').catch(()=>document.querySelector('#notice').textContent='Target rejected')">Refresh</button><p id="notice">Page retained</p></body></html>"""
RESPONSE=b'<p>Unexpected replacement</p>'

def run():
    path=(Action("button","Refresh"),);cfg=Settings(depth=1,settle_ms=800)
    with fixture("fixed",ROOT,HTML,RESPONSE) as a,fixture("buggy",ROOT,HTML,RESPONSE) as b,fixture("fixed",ROOT,HTML,RESPONSE) as c:
        result=replay(a,b,path,cfg);control=replay(a,c,path,cfg)
    kept=all("Target rejected" in r.get("final",{}).get("text",[]) for r in result["before"])
    replaced=all("Unexpected replacement" in r.get("final",{}).get("text",[]) for r in result["after"])
    return {"kind":"historical upstream library regression","fixed":"b98e4f2b12096c216e799b10b0aff1fe9c7a923d","buggy":"df92b295d6b91291ecef97733ba135ac5de565a5","observed":result["status"],"clean_control":control["status"],"passed":kept and replaced and result["status"]=="behavior_changed" and control["status"]=="equivalent_observed","evidence":result,"control_evidence":control}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="htmx-ajax-history.json");a=p.parse_args()
    r=run();Path(a.out).write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k not in ("evidence","control_evidence")},indent=2));raise SystemExit(0 if r["passed"] else 1)
