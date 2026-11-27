"""GHOSTBENCH: consolidate required fixture reports without inventing an accuracy rate."""
import argparse
import json
from pathlib import Path

SUITES={
    "core":{
        "benchmark.json":"synthetic planted regressions and clean controls",
        "upstream-benchmark.json":"upstream example with planted defect",
        "historical-benchmark.json":"historical MDN DOM example",
        "channel-history.json":"historical MDN channel messaging example",
        "todomvc-history.json":"historical TodoMVC reference application",
    },
    "scale":{
        "scale.json":"synthetic action-width scaling",
        "todomvc-scale.json":"historical TodoMVC large-state validation",
    },
}

def summarize(directory,suite):
    rows=[]
    for name,kind in SUITES[suite].items():
        path=Path(directory)/name
        if not path.is_file():
            rows.append({"report":name,"category":kind,"status":"missing","passed":False});continue
        try:
            raw=json.loads(path.read_text(encoding="utf-8"))
            passed=raw.get("passed") is True
            rows.append({"report":name,"category":kind,"status":"passed" if passed else "failed","passed":passed})
        except (ValueError,OSError,AttributeError):
            rows.append({"report":name,"category":kind,"status":"invalid","passed":False})
    return {"schema":"ghostbench.summary/v1","suite":suite,"reports":rows,"passed":all(x["passed"] for x in rows),"limits":"Fixture report pass counts are not bug detection rates. Categories overlap; historical cases are a small selected corpus."}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--suite",choices=SUITES,required=True);p.add_argument("--directory",default=".");p.add_argument("--out",required=True);a=p.parse_args()
    r=summarize(a.directory,a.suite)
    Path(a.out).write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps(r,indent=2))
    raise SystemExit(0 if r["passed"] else 1)
