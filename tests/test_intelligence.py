import copy
import unittest
from ghostdiff.engine import Settings
from dataclasses import asdict
from ghostdiff.intelligence import fingerprint,match_renames
from ghostdiff.diagnostics import diagnose
from ghostdiff.bisect import locate,parse_manifest

def row(name,text="Done"):
    path=[{"role":"button","name":name}]
    outcome={"text_added":[text],"text_removed":[],"route_change":None,"downloads":[],"page_errors":[]}
    snap={"route":"/","text":["Ready"],"actions":path}
    run={"status":"ok","initial":snap,"final":snap,"steps":[{"action":path[0],"outcome":outcome}]}
    return {"path":path,"status":"equivalent_observed","reason":"test","before":[run,copy.deepcopy(run)],"after":[copy.deepcopy(run),copy.deepcopy(run)]}

def evidence(a,b,rows):
    snap={"route":"/","text":["Ready"],"actions":[r["path"][0] for r in rows]}
    run={"status":"ok","initial":snap,"final":snap,"steps":[]}
    root={"path":[],"status":"inventory","reason":"test","before":[run,copy.deepcopy(run)],"after":[copy.deepcopy(run),copy.deepcopy(run)]}
    return {"schema":"ghostdiff.evidence/v1","observation_revision":3,"settings":asdict(Settings()),"before_url":a,"after_url":b,"paths":[root]+rows}

class IntelligenceTests(unittest.TestCase):
    def test_fingerprint_order_and_scope(self):
        a=evidence("a","b",[row("Save"),row("Export")])
        b=copy.deepcopy(a);b["paths"].reverse()
        self.assertEqual(fingerprint(a)["behavior_sha256"],fingerprint(b)["behavior_sha256"])
        b["paths"][next(i for i,r in enumerate(b["paths"]) if r["path"] and r["path"][0]["name"]=="Export")]=row("Export","Changed")
        self.assertNotEqual(fingerprint(a)["behavior_sha256"],fingerprint(b)["behavior_sha256"])
        self.assertEqual(fingerprint(a)["scope_sha256"],fingerprint(b)["scope_sha256"])
    def test_rename_ambiguity(self):
        a=evidence("a","b",[row("Export")])
        b=evidence("b","a",[row("Download")])
        self.assertEqual(match_renames(a,b)["hypotheses"][0]["status"],"review_required")
        b=evidence("b","a",[row("Download"),row("Save")])
        self.assertEqual(match_renames(a,b)["hypotheses"][0]["status"],"ambiguous")
    def test_diagnose(self):
        r=row("Save");r["status"]="behavior_changed"
        for run in r["after"]:run["steps"][0]["outcome"]["http_errors"]=[{"status":503,"path":"/api"}]
        finding=diagnose(evidence("a","b",[r]))["findings"][0]["first_observed_divergence"]
        self.assertEqual(finding["step"],1)
        self.assertEqual(finding["http_errors"][0]["path"],"/api")
    def test_bisect(self):
        rows=[{"commit":f"{i:040x}","url":f"http://localhost:{3000+i}"} for i in range(8)]
        self.assertEqual(parse_manifest({"schema":"ghostdiff.revisions/v1","revisions":rows}),rows)
        p=lambda r:"good" if int(r["commit"],16)<4 else "bad"
        result=locate(rows,p)
        self.assertEqual(result["boundary"]["first_bad"],rows[4]["commit"])
        self.assertLess(len(result["tested"]),len(rows))
        self.assertEqual(locate(rows,p,True)["status"],"observed_boundary")
        self.assertEqual(locate(rows,lambda r:"bad" if int(r["commit"],16) in (2,7) else "good",True)["status"],"non_monotonic")
        self.assertEqual(locate(rows,lambda r:"inconclusive" if r==rows[3] else p(r))["status"],"inconclusive")
