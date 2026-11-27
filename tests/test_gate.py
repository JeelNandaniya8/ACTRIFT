import os
import unittest
from ghostdiff.gate import exit_code
from ghostdiff.engine import Settings,compare
from ghostdiff.demo import serve

class GateTests(unittest.TestCase):
    def test_strict_and_default(self):
        report={"summary":{"equivalent_observed":1},"coverage":{"omitted_budget_branches":0}}
        self.assertEqual(exit_code(report,True),0)
        for extra in ({"skipped_actions":[{}]},{"coverage":{"omitted_budget_branches":2}},{"summary":{"equivalent_observed":1,"unobserved":1}}):
            changed={**report,**extra}
            self.assertEqual(exit_code(changed),0)
            self.assertEqual(exit_code(changed,True),2)
        self.assertEqual(exit_code({**report,"baseline_only_actions":[{}]}),1)
        self.assertEqual(exit_code({"summary":{"equivalent_observed":1,"inconclusive":1}}),2)
        self.assertEqual(exit_code({"summary":{"equivalent_observed":1,"download_changed":1}}),1)
        self.assertEqual(exit_code({"summary":{"equivalent_observed":1}},True),2)

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class CoverageTests(unittest.TestCase):
    def test_missing_action_beyond_budget(self):
        good=b"""<html><body><button onclick="document.querySelector('p').textContent='Saved'">A save</button><button>Z history</button><p>Ready</p></body></html>"""
        bad=good.replace(b"<button>Z history</button>",b"")
        with serve(good) as a,serve(bad) as b:
            report=compare(a,b,Settings(depth=1,budget=2,settle_ms=100))
        self.assertEqual(report["coverage"]["omitted_budget_branches"],1)
        self.assertEqual(report["summary"].get("equivalent_observed"),1)
        self.assertEqual(report["baseline_only_actions"],[
            {"path":[],"action":{"role":"button","name":"Z history"}},
            {"path":[{"role":"button","name":"A save"}],"action":{"role":"button","name":"Z history"}},
        ])
        self.assertEqual(exit_code(report),1)

    def test_exact_budget_not_truncation(self):
        html=b"""<html><body><button onclick="document.querySelector('p').textContent='Saved'">Save</button><p>Ready</p></body></html>"""
        with serve(html) as a,serve(html) as b:
            report=compare(a,b,Settings(depth=1,budget=2,settle_ms=100))
        self.assertTrue(report["coverage"]["budget_reached"])
        self.assertEqual(report["coverage"]["omitted_budget_branches"],0)
        self.assertEqual(exit_code(report,True),0)
