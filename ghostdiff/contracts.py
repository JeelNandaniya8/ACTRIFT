"""Freeze repeatable baseline observations and verify them without a live baseline."""
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256

from playwright.sync_api import sync_playwright
from .engine import Action, Settings, experiment, signature, stable_json, validate_url, has_signal, launch_browser, validate_path


def outcomes(result):
    return [step["outcome"] for step in result["steps"]]


def freeze(evidence):
    if evidence.get("schema") != "ghostdiff.evidence/v1":
        raise ValueError("Unsupported evidence schema")
    if evidence.get("observation_revision") != 3:
        raise ValueError("Evidence uses an older observation format; rerun compare before freezing")
    if evidence.get("backend_reset"):
        raise ValueError("Reset-dependent evidence cannot yet be frozen into ordinary contracts")
    cfg = Settings(**evidence["settings"])
    cfg.validate()
    if cfg.allow_writes or cfg.allow_risky_actions:
        raise ValueError("Write-enabled or risky-action sessions cannot be frozen as read-policy contracts")
    contracts = []
    for row in evidence["paths"]:
        path = row["path"]
        runs = row["before"]
        if not path or len(runs) < 2 or any(r["status"] != "ok" for r in runs):
            continue
        if len({signature(r) for r in runs}) != 1:
            continue
        expected = outcomes(runs[0])
        if any((o.get("page_errors") or o.get("http_errors")) for o in expected) or not any(has_signal(o) for o in expected):
            continue
        key = sha256(stable_json(path).encode()).hexdigest()[:16]
        contracts.append({"id":key,"path":path,"expected":expected})
    if not contracts:
        raise ValueError("No stable, observable baseline journeys to protect")
    return {"schema":"ghostdiff.contracts/v1","observation_revision":3,"authenticated":bool(evidence.get("authenticated_baseline")),"settings":asdict(replace(cfg, executable=None,screenshots=False)),
            "contracts":contracts,"limits":"Exact action names and observed outcomes only. Not a correctness specification."}


def assess(contract, runs):
    if len(runs)<2 or len({signature(r) for r in runs})!=1:
        return "inconclusive"
    run=runs[0]
    if run["status"]=="unmatched" and not run.get("blocked"):
        return "changed"
    if run["status"]!="ok":
        return "inconclusive"
    return "matched" if outcomes(run)==contract["expected"] else "changed"


def verify(data, target, executable=None, aliases=None, storage_state=None):
    validate_url(target)
    if data.get("schema")!="ghostdiff.contracts/v1":
        raise ValueError("Unsupported contract schema")
    if data.get("observation_revision") != 3:
        raise ValueError("Contract observation format changed; rerun compare and freeze")
    if data.get("authenticated") and storage_state is None:
        raise ValueError("Authenticated contracts require an explicit test-account storage state")
    cfg=replace(Settings(**data["settings"]),allow_writes=False,allow_risky_actions=False,executable=executable,screenshots=False)
    cfg.validate()
    contracts=data["contracts"]
    if not 1<=len(contracts)<=200:
        raise ValueError("Contract count must be 1–200")
    ids=set()
    for item in contracts:
        path=item["path"]
        if not 1<=len(path)<=cfg.depth or len(path)!=len(item["expected"]):
            raise ValueError("Invalid path or outcome length")
        if item["id"] in ids:
            raise ValueError("Duplicate contract ID")
        ids.add(item["id"])
        for a in path:
            if a["role"] not in ("button","link","reload") or not isinstance(a["name"],str) or not 1<=len(a["name"])<=120:
                raise ValueError("Unsupported action")
    alias_map=validate_aliases(aliases,contracts)
    rows=[]
    with sync_playwright() as p:
        browser=launch_browser(p,cfg)
        try:
            for item in contracts:
                path=tuple(alias_map.get((item["id"],i),Action(**a)) for i,a in enumerate(item["path"]))
                runs=[experiment(browser,target,path,cfg,storage_state) for _ in range(cfg.repeats)]
                rows.append({"id":item["id"],"path":item["path"],"executed_path":[asdict(a) for a in path],"status":assess(item,runs),"expected":item["expected"],"observed":runs})
        finally:
            browser.close()
    return {"schema":"ghostdiff.verification/v1","target":target,"summary":dict(Counter(r["status"] for r in rows)),"results":rows}


def validate_aliases(aliases, contracts):
    """Explicit per-contract action substitutions; never infer or auto-approve."""
    if aliases is None:
        return {}
    if not isinstance(aliases,dict) or aliases.get("schema")!="ghostdiff.aliases/v1":
        raise ValueError("Unsupported aliases schema")
    items=aliases["aliases"]
    if not isinstance(items,list) or len(items)>1000:
        raise ValueError("Invalid aliases list")
    known={x["id"]:x["path"] for x in contracts}
    mapping={}
    for entry in items:
        if set(entry)!={"contract_id","step","from","to"}:
            raise ValueError("Invalid alias fields")
        cid,i=entry["contract_id"],entry["step"]
        if cid not in known or type(i) is not int or not 0<=i<len(known[cid]):
            raise ValueError("Alias refers to unknown contract step")
        original=known[cid][i]
        if entry["from"]!=original["name"] or original["role"] not in ("button","link"):
            raise ValueError("Alias source does not match original action")
        target=entry["to"]
        if not isinstance(target,str) or not 1<=len(target)<=120 or not target.strip():
            raise ValueError("Invalid alias destination")
        if (cid,i) in mapping:
            raise ValueError("Duplicate alias")
        mapping[cid,i]=Action(original["role"],target)
    return mapping


def recapture(data,target,executable=None,storage_state=None):
    """Re-observe old contracts on a trusted baseline. Never silently drop a path."""
    validate_url(target)
    if data.get("schema")!="ghostdiff.contracts/v1" or data.get("observation_revision",1) not in (1,2,3):
        raise ValueError("Unsupported contract revision")
    if data.get("authenticated") and storage_state is None:
        raise ValueError("Authenticated contracts require test-account storage state")
    cfg=replace(Settings(**data["settings"]),executable=executable,screenshots=False)
    cfg.validate()
    if cfg.allow_writes or cfg.allow_risky_actions:
        raise ValueError("Write-enabled or risky-action contracts cannot be recaptured")
    contracts=data["contracts"]
    if not 1<=len(contracts)<=200:
        raise ValueError("Invalid contract count")
    seen=set()
    for item in contracts:
        path=tuple(Action(**a) for a in item["path"])
        validate_path(path,cfg)
        if not path or len(item["expected"])!=len(path) or item["id"] in seen:
            raise ValueError("Invalid legacy contract")
        seen.add(item["id"])
        for old in item["expected"]:
            if not isinstance(old,dict) or not {"text_added","text_removed","route_change","downloads"}<=set(old):
                raise ValueError("Legacy outcome lacks required fields")
    upgraded=[]
    failures=[]
    with sync_playwright() as p:
        browser=launch_browser(p,cfg)
        try:
            for item in contracts:
                path=tuple(Action(**a) for a in item["path"])
                runs=[experiment(browser,target,path,cfg,storage_state) for _ in range(cfg.repeats)]
                result=runs[0]
                if any(r["status"]!="ok" for r in runs) or len({signature(r) for r in runs})!=1:
                    failures.append(item["id"])
                    continue
                actual=outcomes(result)
                if len(actual)!=len(item["expected"]) or any((o.get("page_errors") or o.get("http_errors")) for o in actual) or not any(has_signal(o) for o in actual):
                    failures.append(item["id"])
                    continue
                if any(any(k not in new or new[k]!=v for k,v in old.items()) for old,new in zip(item["expected"],actual)):
                    failures.append(item["id"])
                    continue
                upgraded.append({**item,"expected":actual})
        finally:
            browser.close()
    if failures:
        raise ValueError("Recapture refused: legacy observations not preserved for "+", ".join(failures))
    return {"schema":"ghostdiff.contracts/v1","observation_revision":3,"authenticated":storage_state is not None,
            "settings":asdict(replace(cfg,executable=None)),"contracts":upgraded,
            "recaptured_from_revision":data.get("observation_revision",1),
            "limits":"Recaptured from an explicitly supplied trusted baseline; legacy observable fields matched. Not a correctness specification."}


def generate_test():
    return '''"""Generated regression suite. Run only against a disposable local application."""
import json
import os
from pathlib import Path
import unittest
from ghostdiff.contracts import verify

class ProtectedBehaviors(unittest.TestCase):
    def test_contracts(self):
        target = os.environ["GHOSTDIFF_TARGET"]
        if os.environ.get("GHOSTDIFF_ALLOW_ACTIONS") != "1":
            self.fail("Set GHOSTDIFF_ALLOW_ACTIONS=1 only for authorized disposable apps")
        source = Path(os.environ.get("GHOSTDIFF_CONTRACTS", "contracts.json"))
        result = verify(json.loads(source.read_text(encoding="utf-8")), target, storage_state=os.environ.get("GHOSTDIFF_STORAGE_STATE"))
        self.assertEqual(set(result["summary"]), {"matched"}, json.dumps(result["summary"]))

if __name__ == "__main__":
    unittest.main()
'''
