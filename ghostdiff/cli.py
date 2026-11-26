"""Command line interface and portable evidence report."""
import argparse
import html
import json
from pathlib import Path
import sys
from .engine import Action, Settings, compare, replay
from .demo import app, serve

def report_html(report):
    escape = lambda x: html.escape(str(x))
    rows = []
    for i, row in enumerate(report["paths"]):
        title = " / ".join(a["name"] for a in row["path"]) or "Initial inventory"
        evidence = json.dumps({"baseline":row["before"],"candidate":row["after"]}, indent=2, ensure_ascii=False)
        rows.append(f'<details><summary>{i:02d} · {escape(title)} <b>{escape(row["status"])}</b></summary><p>{escape(row["reason"])}</p><pre>{escape(evidence)}</pre></details>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ghostdiff evidence</title><style>body{font:16px/1.6 system-ui;margin:40px auto;max-width:960px;padding:0 20px;color:#26352f;background:#faf9f6}h1{font-size:3rem;letter-spacing:-.05em}details{border-top:1px solid #bbc5bd;padding:16px 0}summary{cursor:pointer}b{float:right;color:#315c50}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf0ec;padding:16px}footer{margin-top:36px}</style><h1>Behavior, compared.</h1><p>GHOSTDIFF / EVIDENCE V1</p><p>'+escape(report["before_url"])+' → '+escape(report["after_url"])+'</p><pre>'+escape(json.dumps(report["summary"],indent=2))+'</pre>'+''.join(rows)+'<footer>'+escape(report["limits"])+'</footer></html>'

def save(report, target):
    out=Path(target)
    out.mkdir(parents=True,exist_ok=True)
    (out/"evidence.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"report.html").write_text(report_html(report),encoding="utf-8")
    for i,row in enumerate(report["paths"]):
        print(i,row["status"]," > ".join(x["name"] for x in row["path"]) or "Initial inventory")
    print("Summary:",json.dumps(report["summary"],sort_keys=True))
    print("Report:",out/"report.html")

def main(argv=None):
    parser=argparse.ArgumentParser(prog="ghostdiff")
    sub=parser.add_subparsers(dest="command",required=True)
    for name in ("demo","compare"):
        p=sub.add_parser(name)
        p.add_argument("--depth",type=int,default=2)
        p.add_argument("--budget",type=int,default=30)
        p.add_argument("--settle-ms",type=int,default=180)
        p.add_argument("--timeout-ms",type=int,default=2500)
        p.add_argument("--repeats",type=int,default=2)
        p.add_argument("--browser-executable")
        p.add_argument("--out",default="ghostdiff-report")
        if name=="compare":
            p.add_argument("--before",required=True)
            p.add_argument("--after",required=True)
            p.add_argument("--allow-actions",action="store_true")
            p.add_argument("--allow-writes",action="store_true")
            p.add_argument("--fail-on-change",action="store_true")
        else:
            p.add_argument("--clean",action="store_true")
    p=sub.add_parser("replay")
    p.add_argument("evidence")
    p.add_argument("--index",type=int,required=True)
    p.add_argument("--before",required=True)
    p.add_argument("--after",required=True)
    p.add_argument("--allow-actions",action="store_true")
    p.add_argument("--allow-writes",action="store_true")
    p.add_argument("--browser-executable")
    a=parser.parse_args(argv)
    try:
        if a.command=="replay":
            if not a.allow_actions: parser.error("replay requires --allow-actions")
            if a.index<0: raise ValueError("Index must be nonnegative")
            data=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
            if data["schema"]!="ghostdiff.evidence/v1": raise ValueError("Unsupported evidence schema")
            row=data["paths"][a.index]
            settings={**data["settings"],"allow_writes":a.allow_writes,"executable":a.browser_executable}
            result=replay(a.before,a.after,tuple(Action(**x) for x in row["path"]),Settings(**settings))
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 2 if result["status"]=="inconclusive" else 0
        cfg=Settings(depth=a.depth,budget=a.budget,settle_ms=a.settle_ms,timeout_ms=a.timeout_ms,repeats=a.repeats,allow_writes=getattr(a,"allow_writes",False),executable=a.browser_executable)
        if a.command=="demo":
            with serve(app()) as before, serve(app(broken=not a.clean,redesign=True)) as after:
                report=compare(before,after,cfg)
            report["demo"]={"clean":a.clean,"planted_faults":[] if a.clean else ["export no-op","history removed","theme not persisted"]}
        else:
            if not a.allow_actions: parser.error("compare requires --allow-actions")
            report=compare(a.before,a.after,cfg)
        save(report,a.out)
        if getattr(a,"fail_on_change",False):
            if report["summary"].get("inconclusive"): return 2
            if any(report["summary"].get(k) for k in ("unmatched","behavior_changed","download_changed")): return 1
        return 0
    except (ValueError,OSError,KeyError,IndexError,TypeError) as exc:
        print(f"ghostdiff: {exc}",file=sys.stderr)
        return 2
