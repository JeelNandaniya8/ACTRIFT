"""Command line interface and portable evidence report."""
import argparse
import html
import json
from pathlib import Path
import sys
from playwright.sync_api import Error as BrowserError
from .engine import Action, Settings, compare, replay, launch_browser
from .demo import app, serve
from .contracts import freeze, verify, generate_test, recapture
from .observatory import render_observatory
from .report_media import screenshots, without_images
from .scenario import run_journeys
from .gate import exit_code
from .intelligence import fingerprint,match_renames
from .diagnostics import diagnose
from .bisect import bisect
from .gitintel import git_bisect
from .sourceintel import localize
from .config import parse_config
from .history import timeline
from .history_store import record,history
from .sourcemap import load_maps
from .agent import summarize as agent_summary

def report_html(report):
    escape = lambda x: html.escape(str(x))
    rows = []
    for i, row in enumerate(report["paths"]):
        title = row.get("name") or " / ".join(a["name"] for a in row["path"]) or "Initial inventory"
        evidence = json.dumps({"baseline":without_images(row["before"]),"candidate":without_images(row["after"])}, indent=2, ensure_ascii=False)
        rows.append(f'<details><summary>{i:02d} · {escape(title)} <b>{escape(row["status"])}</b></summary><p>{escape(row["reason"])}</p>{screenshots(row)}<pre>{escape(evidence)}</pre></details>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ghostdiff evidence</title><style>body{font:16px/1.6 system-ui;margin:40px auto;max-width:960px;padding:0 20px;color:#26352f;background:#faf9f6}h1{font-size:3rem;letter-spacing:-.05em}details{border-top:1px solid #bbc5bd;padding:16px 0}summary{cursor:pointer}b{float:right;color:#315c50}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf0ec;padding:16px}footer{margin-top:36px}</style><h1>Behavior, compared.</h1><p>GHOSTDIFF / EVIDENCE V1</p><p>'+escape(report["before_url"])+' → '+escape(report["after_url"])+'</p><pre>'+escape(json.dumps(report["summary"],indent=2))+'</pre><h2>Exploration coverage</h2><pre>'+escape(json.dumps(report.get("coverage",{}),indent=2))+'</pre><details><summary>Baseline-only actions (review)</summary><pre>'+escape(json.dumps(report.get("baseline_only_actions",[]),indent=2))+'</pre></details>'+''.join(rows)+'<footer>'+escape(report["limits"])+'</footer></html>'

def save(report, target, summary_only=False):
    out=Path(target)
    out.mkdir(parents=True,exist_ok=True)
    (out/"evidence.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"report.html").write_text(report_html(report),encoding="utf-8")
    (out/"observatory.html").write_text(render_observatory(report),encoding="utf-8")
    if report.get("schema")=="ghostdiff.evidence/v1":
        (out/"diagnostics.json").write_text(json.dumps(diagnose(report),indent=2,ensure_ascii=False),encoding="utf-8")
    if not summary_only:
        for i,row in enumerate(report["paths"]):
            print(i,row["status"]," > ".join(x["name"] for x in row["path"]) or "Initial inventory")
    print("Summary:",json.dumps(report["summary"],sort_keys=True))
    print("Coverage:",json.dumps(report.get("coverage",{}),sort_keys=True))
    print("Performance:",json.dumps(report.get("performance",{}),sort_keys=True))
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
        p.add_argument("--browser",choices=("chromium","firefox","webkit"),default="chromium")
        p.add_argument("--out",default="ghostdiff-report")
        p.add_argument("--parallel",action="store_true",help="Compare independent local versions concurrently in separate browsers")
        p.add_argument("--summary-only",action="store_true",help="Suppress observed action names in console output")
        p.add_argument("--ignore",action="append",default=[],help="Comma-separated exact action names to skip; repeatable")
        p.add_argument("--mask-text",action="append",default=[],help="CSS selector to exclude from text observations; repeatable")
        p.add_argument("--observe-api",action="append",default=[],help="Exact local JSON API path to observe; repeatable, synthetic data only")
        p.add_argument("--screenshots",action="store_true",help="Capture viewport images; may contain sensitive data")
        p.add_argument("--allow-risky-actions",action="store_true",help="Disable heuristic risky-name filter; only isolated disposable apps")
        if name=="compare":
            p.add_argument("--before-state",help="Local synthetic test-account Playwright storage state JSON")
            p.add_argument("--after-state",help="Separate candidate test-account storage state JSON")
            p.add_argument("--before",required=True)
            p.add_argument("--after",required=True)
            p.add_argument("--allow-actions",action="store_true")
            p.add_argument("--allow-writes",action="store_true")
            p.add_argument("--reset-backend",action="store_true",help="Explicitly POST the fixed reset endpoint before each observation; disposable numeric-loopback servers only")
            p.add_argument("--fail-on-change",action="store_true")
            p.add_argument("--require-complete",action="store_true",help="Also fail on skipped, budget-omitted or unobserved journeys within selected depth")
        else:
            p.add_argument("--clean",action="store_true")
    p=sub.add_parser("doctor",help="Check browser installation and launch")
    p.add_argument("--browser",choices=("chromium","firefox","webkit"),default="chromium")
    p=sub.add_parser("replay")
    p.add_argument("evidence")
    p.add_argument("--index",type=int,required=True)
    p.add_argument("--before-state"); p.add_argument("--after-state"); p.add_argument("--allow-risky-actions",action="store_true")
    p.add_argument("--before",required=True)
    p.add_argument("--after",required=True)
    p.add_argument("--allow-actions",action="store_true")
    p.add_argument("--allow-writes",action="store_true")
    p.add_argument("--browser-executable")
    p=sub.add_parser("freeze",help="Create executable baseline contracts from stable evidence")
    p.add_argument("evidence"); p.add_argument("--out",default="contracts.json"); p.add_argument("--test-out")
    p=sub.add_parser("verify",help="Replay protected behaviors against a local candidate")
    p.add_argument("contracts"); p.add_argument("--target",required=True); p.add_argument("--allow-actions",action="store_true"); p.add_argument("--browser-executable"); p.add_argument("--out",default="verification.json")
    p.add_argument("--aliases",help="Explicitly reviewed per-contract action mapping JSON")
    p.add_argument("--storage-state")
    p=sub.add_parser("recapture",help="Re-observe legacy contracts against a trusted baseline")
    p.add_argument("contracts"); p.add_argument("--baseline",required=True); p.add_argument("--out",required=True); p.add_argument("--allow-actions",action="store_true"); p.add_argument("--browser-executable")
    p.add_argument("--storage-state")
    p=sub.add_parser("journey",help="Compare explicit synthetic form journeys")
    p.add_argument("spec"); p.add_argument("--before",required=True); p.add_argument("--after",required=True); p.add_argument("--allow-actions",action="store_true"); p.add_argument("--before-state"); p.add_argument("--after-state"); p.add_argument("--screenshots",action="store_true"); p.add_argument("--out",default="journey-report")
    p=sub.add_parser("fingerprint",help="Hash stable observed behavior")
    p.add_argument("evidence");p.add_argument("--side",choices=("before","after"),default="before");p.add_argument("--out")
    p=sub.add_parser("match",help="Review rename hypotheses from forward and reverse evidence")
    p.add_argument("forward");p.add_argument("reverse");p.add_argument("--out")
    p=sub.add_parser("diagnose",help="Locate first observed divergences")
    p.add_argument("evidence");p.add_argument("--out")
    p=sub.add_parser("bisect",help="Locate regression among pre-provisioned ordered local revisions")
    p.add_argument("manifest");p.add_argument("contracts");p.add_argument("--allow-actions",action="store_true");p.add_argument("--exhaustive",action="store_true");p.add_argument("--out")
    p=sub.add_parser("git-bisect",help="Automatically serve and test local static Git revisions")
    p.add_argument("repo");p.add_argument("--good",required=True);p.add_argument("--bad",required=True);p.add_argument("--site",default=".");p.add_argument("--contracts");p.add_argument("--allow-actions",action="store_true");p.add_argument("--exhaustive",action="store_true");p.add_argument("--out")
    p=sub.add_parser("localize",help="Correlate observed divergence with changed Git source hunks")
    p.add_argument("evidence");p.add_argument("--repo",required=True);p.add_argument("--good",required=True);p.add_argument("--bad",required=True);p.add_argument("--source-maps");p.add_argument("--out")
    p=sub.add_parser("compare-config",help="Compare local versions using reviewed JSON settings")
    p.add_argument("config");p.add_argument("--allow-actions",action="store_true");p.add_argument("--out",default="ghostdiff-report")
    p=sub.add_parser("timeline",help="Compare scoped fingerprints in an ordered local history")
    p.add_argument("manifest");p.add_argument("--out")
    p=sub.add_parser("agent-summary",help="Emit a data-minimized machine-readable evidence summary")
    p.add_argument("evidence");p.add_argument("--strict",action="store_true")
    p=sub.add_parser("agent-run",help="Run an explicitly authorized local comparison and emit JSON only")
    p.add_argument("config");p.add_argument("--allow-actions",action="store_true");p.add_argument("--evidence-out")
    p=sub.add_parser("history-record",help="Append a scoped fingerprint to local SQLite history")
    p.add_argument("evidence");p.add_argument("--db",required=True);p.add_argument("--project",required=True);p.add_argument("--revision",required=True);p.add_argument("--side",choices=("before","after"),default="before")
    p=sub.add_parser("history-show",help="Read local scoped fingerprint history")
    p.add_argument("--db",required=True);p.add_argument("--project",required=True);p.add_argument("--limit",type=int,default=100)
    a=parser.parse_args(argv)
    if a.command in ("agent-summary","agent-run"):
        try:
            if a.command=="agent-summary":
                path=Path(a.evidence)
                if path.stat().st_size>32*1024*1024:raise ValueError("Evidence too large")
                result=agent_summary(json.loads(path.read_text(encoding="utf-8")),a.strict)
            else:
                if not a.allow_actions:raise ValueError("Explicit authorization required")
                path=Path(a.config)
                if path.stat().st_size>65536:raise ValueError("Config too large")
                before,after,cfg,bidirectional,strict=parse_config(json.loads(path.read_text(encoding="utf-8")))
                if bidirectional or cfg.screenshots:raise ValueError("Agent runs require forward-only, screenshot-free configuration")
                if a.evidence_out and Path(a.evidence_out).exists():raise ValueError("Evidence destination already exists")
                report=compare(before,after,cfg)
                result=agent_summary(report,strict)
                if a.evidence_out:
                    with Path(a.evidence_out).open("x",encoding="utf-8") as fp:
                        json.dump(report,fp,ensure_ascii=False,indent=2)
            print(json.dumps(result,sort_keys=True))
            return result["exit_code"]
        except KeyboardInterrupt:
            print(json.dumps({"schema":"ghostdiff.agent-result/v1","execution_status":"interrupted","exit_code":130}))
            return 130
        except (ValueError,OSError,KeyError,IndexError,TypeError,AttributeError,BrowserError,RecursionError):
            print(json.dumps({"schema":"ghostdiff.agent-result/v1","execution_status":"error","exit_code":2,"reason":"Invalid input, missing authorization or execution failure"}))
            return 2
    try:
        if a.command=="compare-config":
            if not a.allow_actions:parser.error("compare-config requires --allow-actions")
            before,after,cfg,bidirectional,strict=parse_config(json.loads(Path(a.config).read_text(encoding="utf-8")))
            forward=compare(before,after,cfg)
            save(forward,a.out)
            if bidirectional:
                reverse=compare(after,before,cfg)
                save(reverse,Path(a.out)/"reverse")
                hypotheses=match_renames(forward,reverse)
                (Path(a.out)/"rename-hypotheses.json").write_text(json.dumps(hypotheses,indent=2),encoding="utf-8")
            # New candidate actions are reported in reverse evidence, not used as baseline failures.
            return exit_code(forward,strict=strict)
        if a.command in ("history-record","history-show"):
            result=record(a.db,a.project,a.revision,json.loads(Path(a.evidence).read_text(encoding="utf-8")),a.side) if a.command=="history-record" else history(a.db,a.project,a.limit)
            print(json.dumps(result,indent=2))
            return 0
        if a.command=="timeline":
            manifest=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
            if not isinstance(manifest,dict) or set(manifest)!={"schema","revisions"} or manifest["schema"]!="ghostdiff.timeline-input/v1":
                raise ValueError("Unsupported timeline manifest")
            entries=[]
            for item in manifest["revisions"]:
                if set(item)!={"revision","evidence","side"}:raise ValueError("Invalid timeline entry")
                path=Path(a.manifest).resolve().parent/item["evidence"]
                entries.append((item["revision"],json.loads(path.read_text(encoding="utf-8")),item["side"]))
            result=timeline(entries)
            encoded=json.dumps(result,indent=2,ensure_ascii=False)
            if a.out:Path(a.out).write_text(encoded,encoding="utf-8")
            else:print(encoded)
            return 0
        if a.command in ("fingerprint","match","diagnose","bisect","git-bisect","localize"):
            def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
            if a.command=="fingerprint": result=fingerprint(load(a.evidence),a.side)
            elif a.command=="match": result=match_renames(load(a.forward),load(a.reverse))
            elif a.command=="diagnose": result=diagnose(load(a.evidence))
            elif a.command=="localize": result=localize(a.repo,a.good,a.bad,load(a.evidence),load_maps(a.source_maps) if a.source_maps else None)
            elif a.command=="git-bisect":
                if not a.allow_actions:parser.error("git-bisect requires --allow-actions")
                result=git_bisect(a.repo,a.good,a.bad,a.site,load(a.contracts) if a.contracts else None,a.exhaustive)
            else:
                if not a.allow_actions: parser.error("bisect requires --allow-actions")
                result=bisect(load(a.manifest),load(a.contracts),a.exhaustive)
            encoded=json.dumps(result,indent=2,ensure_ascii=False)
            if a.out:Path(a.out).write_text(encoded,encoding="utf-8")
            else:print(encoded)
            return 2 if a.command in ("bisect","git-bisect") and result["boundary"] is None else 0
        if a.command=="journey":
            if not a.allow_actions: parser.error("journey requires --allow-actions")
            report=run_journeys(json.loads(Path(a.spec).read_text(encoding="utf-8")),a.before,a.after,Settings(screenshots=a.screenshots),a.before_state,a.after_state)
            out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
            (out/"evidence.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
            (out/"report.html").write_text(report_html(report),encoding="utf-8")
            print(json.dumps(report["summary"],sort_keys=True))
            if report["summary"].get("inconclusive") or report["summary"].get("unobserved"): return 2
            return 0 if set(report["summary"])=={"equivalent_observed"} else 1
        if a.command=="doctor":
            from playwright.sync_api import sync_playwright
            from . import __version__
            with sync_playwright() as p:
                browser=launch_browser(p,Settings(browser=a.browser))
                try:
                    print(f"GHOSTDIFF {__version__}; {a.browser} {browser.version}; browser launch OK")
                finally:
                    browser.close()
            return 0
        if a.command=="freeze":
            data=freeze(json.loads(Path(a.evidence).read_text(encoding="utf-8")))
            Path(a.out).write_text(json.dumps(data,indent=2),encoding="utf-8")
            if a.test_out: Path(a.test_out).write_text(generate_test(),encoding="utf-8")
            print(f"Saved {len(data['contracts'])} stable baseline journeys to {a.out}")
            return 0
        if a.command=="recapture":
            if not a.allow_actions: parser.error("recapture requires --allow-actions")
            target=Path(a.out)
            if target.exists(): raise ValueError("Recapture destination already exists; choose a new file")
            result=recapture(json.loads(Path(a.contracts).read_text(encoding="utf-8")),a.baseline,a.browser_executable,a.storage_state)
            with target.open("x",encoding="utf-8") as fp: json.dump(result,fp,indent=2)
            print(f"Recaptured {len(result['contracts'])} contracts; review before use")
            return 0
        if a.command=="verify":
            if not a.allow_actions: parser.error("verify requires --allow-actions")
            aliases=json.loads(Path(a.aliases).read_text(encoding="utf-8")) if a.aliases else None
            result=verify(json.loads(Path(a.contracts).read_text(encoding="utf-8")),a.target,a.browser_executable,aliases,a.storage_state)
            Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
            print(json.dumps(result["summary"],sort_keys=True))
            return 2 if result["summary"].get("inconclusive") else 1 if result["summary"].get("changed") else 0
        if a.command=="replay":
            if not a.allow_actions: parser.error("replay requires --allow-actions")
            if a.index<0: raise ValueError("Index must be nonnegative")
            data=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
            if data["schema"]!="ghostdiff.evidence/v1": raise ValueError("Unsupported evidence schema")
            if data.get("backend_reset"):raise ValueError("Reset-dependent evidence requires a fresh explicitly authorized comparison")
            row=data["paths"][a.index]
            if (data.get("authenticated_baseline") and not a.before_state) or (data.get("authenticated_candidate") and not a.after_state): raise ValueError("Replay requires explicit storage states for authenticated versions")
            settings={**data["settings"],"allow_writes":a.allow_writes,"allow_risky_actions":a.allow_risky_actions,"executable":a.browser_executable}
            result=replay(a.before,a.after,tuple(Action(**x) for x in row["path"]),Settings(**settings),a.before_state,a.after_state)
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 2 if result["status"]=="inconclusive" else 0
        cfg=Settings(depth=a.depth,budget=a.budget,settle_ms=a.settle_ms,timeout_ms=a.timeout_ms,repeats=a.repeats,allow_writes=getattr(a,"allow_writes",False),executable=a.browser_executable,browser=a.browser,ignore=tuple(x.strip() for entry in a.ignore for x in entry.split(",") if x.strip()),mask_text=tuple(a.mask_text),screenshots=a.screenshots,allow_risky_actions=a.allow_risky_actions,parallel=a.parallel,api_paths=tuple(a.observe_api))
        if a.command=="demo":
            with serve(app()) as before, serve(app(broken=not a.clean,redesign=True)) as after:
                report=compare(before,after,cfg)
            report["demo"]={"clean":a.clean,"planted_faults":[] if a.clean else ["export no-op","history removed","theme not persisted"]}
        else:
            if not a.allow_actions: parser.error("compare requires --allow-actions")
            report=compare(a.before,a.after,cfg,a.before_state,a.after_state,reset=a.reset_backend)
        save(report,a.out,a.summary_only)
        if getattr(a,"fail_on_change",False) or getattr(a,"require_complete",False):
            return exit_code(report,strict=a.require_complete)
        return 0
    except KeyboardInterrupt:
        print("ghostdiff: interrupted; no complete result",file=sys.stderr)
        return 130
    except BrowserError as exc:
        print(f"ghostdiff: browser unavailable or failed: {str(exc).splitlines()[0]}",file=sys.stderr)
        print("Install the requested browser with python -m playwright install <browser>; run ghostdiff doctor --browser <browser>",file=sys.stderr)
        return 2
    except (ValueError,OSError,KeyError,IndexError,TypeError,AttributeError) as exc:
        print(f"ghostdiff: {exc}",file=sys.stderr)
        return 2
