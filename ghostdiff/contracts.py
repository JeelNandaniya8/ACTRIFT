"""Freeze repeatable baseline observations and verify them without a live baseline."""
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256

from playwright.sync_api import sync_playwright
from .engine import Action, Settings, experiment, signature, stable_json, validate_url, has_signal, launch_browser


def outcomes(result):
    return [step["outcome"] for step in result["steps"]]


def freeze(evidence):
    if evidence.get("schema") != "ghostdiff.evidence/v1":
        raise ValueError("Unsupported evidence schema")
    if evidence.get("observation_revision") != 2:
        raise ValueError("Evidence uses an older observation format; rerun compare before freezing")
    cfg = Settings(**evidence["settings"])
    cfg.validate()
    if cfg.allow_writes:
        raise ValueError("Write-enabled sessions cannot be frozen as read-policy contracts")
    contracts = []
    for row in evidence["paths"]:
        path = row["path"]
        runs = row["before"]
        if not path or len(runs) < 2 or any(r["status"] != "ok" for r in runs):
            continue
        if len({signature(r) for r in runs}) != 1:
            continue
        expected = outcomes(runs[0])
        if not any(has_signal(o) for o in expected):
            continue
        key = sha256(stable_json(path).encode()).hexdigest()[:16]
        contracts.append({"id":key,"path":path,"expected":expected})
    if not contracts:
        raise ValueError("No stable, observable baseline journeys to protect")
    return {"schema":"ghostdiff.contracts/v1","observation_revision":2,"settings":asdict(replace(cfg, executable=None)),
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


def verify(data, target, executable=None):
    validate_url(target)
    if data.get("schema")!="ghostdiff.contracts/v1":
        raise ValueError("Unsupported contract schema")
    if data.get("observation_revision") != 2:
        raise ValueError("Contract observation format changed; rerun compare and freeze")
    cfg=replace(Settings(**data["settings"]),allow_writes=False,executable=executable)
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
    rows=[]
    with sync_playwright() as p:
        browser=launch_browser(p,cfg)
        try:
            for item in contracts:
                path=tuple(Action(**a) for a in item["path"])
                runs=[experiment(browser,target,path,cfg) for _ in range(cfg.repeats)]
                rows.append({"id":item["id"],"path":item["path"],"status":assess(item,runs),"expected":item["expected"],"observed":runs})
        finally:
            browser.close()
    return {"schema":"ghostdiff.verification/v1","target":target,"summary":dict(Counter(r["status"] for r in rows)),"results":rows}


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
        result = verify(json.loads(source.read_text(encoding="utf-8")), target)
        self.assertEqual(set(result["summary"]), {"matched"}, json.dumps(result["summary"]))

if __name__ == "__main__":
    unittest.main()
'''
