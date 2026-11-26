import unittest
from ghostdiff.contracts import freeze, assess, generate_test
from ghostdiff.engine import Settings
from ghostdiff.observatory import render_observatory
from dataclasses import asdict

def fixture():
    a={"role":"button","name":"Export <script>"}
    o={"text_added":[],"text_removed":[],"route_change":None,"downloads":[{"name":"example.pdf","bytes":30}]}
    snap={"route":"/","text":[],"actions":[a]}
    run={"status":"ok","initial":snap,"final":snap,"steps":[{"action":a,"outcome":o}]}
    root={"path":[],"status":"inventory","reason":"root","before":[run,run],"after":[run,run]}
    row={"path":[a],"status":"download_changed","reason":"changed","before":[run,run],"after":[run,run]}
    return {"schema":"ghostdiff.evidence/v1","settings":asdict(Settings()),"paths":[root,row],"summary":{"inventory":1,"download_changed":1},"limits":"test"},run

class ContractTests(unittest.TestCase):
    def test_freeze_and_match(self):
        e,r=fixture();data=freeze(e)
        self.assertEqual(len(data["contracts"]),1)
        self.assertEqual(assess(data["contracts"][0],[r,r]),"matched")
    def test_changed(self):
        e,r=fixture();contract=freeze(e)["contracts"][0]
        self.assertEqual(assess(contract,[{"status":"unmatched"}]*2),"changed")
    def test_unstable(self):
        e,r=fixture();contract=freeze(e)["contracts"][0]
        self.assertEqual(assess(contract,[r,{"status":"inconclusive"}]),"inconclusive")
    def test_no_stable_contracts(self):
        e,r=fixture();e["paths"][1]["before"]=[r,{"status":"inconclusive"}]
        with self.assertRaises(ValueError): freeze(e)
    def test_write_enabled_rejected(self):
        e,r=fixture();e["settings"]["allow_writes"]=True
        with self.assertRaises(ValueError): freeze(e)
    def test_generated_python(self):
        compile(generate_test(),"generated_test.py","exec")
    def test_observatory_escapes(self):
        e,r=fixture();html=render_observatory(e)
        self.assertIn("Export &lt;script&gt;",html)
        self.assertNotIn("Export <script>",html)


import os
from ghostdiff.contracts import verify
from ghostdiff.demo import app, serve
from ghostdiff.engine import compare

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","enable browser tests explicitly")
class BrowserContractTests(unittest.TestCase):
    def test_verify_good_and_bad(self):
        with serve(app()) as baseline, serve(app(broken=True)) as broken, serve(app(redesign=True)) as clean:
            cfg=Settings(depth=1,budget=8,settle_ms=150)
            evidence=compare(baseline,broken,cfg)
            contracts=freeze(evidence)
            good_result=verify(contracts,clean)
            bad_result=verify(contracts,broken)
        self.assertEqual(set(good_result["summary"]),{"matched"})
        self.assertGreater(bad_result["summary"].get("changed",0),0)
        self.assertNotIn("inconclusive",bad_result["summary"])
