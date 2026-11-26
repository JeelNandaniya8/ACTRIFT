import os
import unittest
from ghostdiff.engine import Settings, compare, compare_path, delta, validate_url
from ghostdiff.demo import app, serve, pdf_bytes

def sample(outcome=None):
    snap={"route":"/","text":["hello"],"actions":[]}
    return {"status":"ok","initial":snap,"final":snap,"steps":[] if outcome is None else [{"outcome":outcome}]}

class UnitTests(unittest.TestCase):
    def test_loopback_only(self):
        for url in ["http://localhost:1234","http://127.0.0.1","http://[::1]:80"]: validate_url(url)
        for url in ["https://example.org","file:///tmp/x","http://user@localhost","http://localhost.evil.org"]:
            with self.assertRaises(ValueError): validate_url(url)
    def test_limits(self):
        Settings().validate()
        for settings in [Settings(depth=0),Settings(repeats=1),Settings(budget=201)]:
            with self.assertRaises(ValueError): settings.validate()
    def test_delta(self):
        self.assertEqual(delta({"text":["a"],"route":"/"},{"text":["b"],"route":"/next"},[]),{"text_added":["b"],"text_removed":["a"],"route_change":"/next","downloads":[]})
    def test_outcome_classification(self):
        x={"text_added":[],"text_removed":[],"route_change":None,"downloads":[]}
        y={**x,"downloads":[{"name":"report.pdf"}]}
        z={**x,"text_added":["changed"]}
        for a,b,status in [(z,z,"equivalent_observed"),(x,y,"download_changed"),(x,z,"behavior_changed")]:
            self.assertEqual(compare_path([sample(a)]*2,[sample(b)]*2)[0],status)
        self.assertEqual(compare_path([sample(x)]*2,[sample(y),sample(z)])[0],"inconclusive")
    def test_pdf_fixture(self):
        self.assertTrue(pdf_bytes().startswith(b"%PDF-1.4"))

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","enable browser tests explicitly")
class BrowserTests(unittest.TestCase):
    def compare_demo(self,broken):
        with serve(app()) as a, serve(app(broken=broken,redesign=True)) as b:
            return compare(a,b,Settings(depth=2,budget=30,settle_ms=100))
    def test_faults(self):
        report=self.compare_demo(True)
        paths={tuple(x["name"] for x in r["path"]):r["status"] for r in report["paths"]}
        self.assertEqual(paths.get(("Export PDF",)),"download_changed")
        self.assertEqual(paths.get(("Search history",)),"unmatched")
        self.assertEqual(paths.get(("Toggle theme","Reload page")),"behavior_changed")
    def test_clean(self):
        report=self.compare_demo(False)
        self.assertGreater(report["summary"].get("equivalent_observed",0),0)
        self.assertEqual(set(report["summary"])-{"inventory","equivalent_observed","unobserved"},set())


class ReliabilityTests(unittest.TestCase):
    def test_duplicate_text(self):
        before={"text":["item"],"route":"/"}
        after={"text":["item","item"],"route":"/"}
        self.assertEqual(delta(before,after,[])["text_added"],["item"])
        self.assertEqual(delta(after,before,[])["text_removed"],["item"])

    def test_action_availability(self):
        a={"role":"button","name":"Next"}
        before={"text":[],"route":"/","actions":[]}
        after={"text":[],"route":"/","actions":[a]}
        self.assertEqual(delta(before,after,[])["actions_added"],[a])
        self.assertEqual(delta(after,before,[])["actions_removed"],[a])

    def test_no_observable_effect(self):
        x={"text_added":[],"text_removed":[],"route_change":None,"downloads":[]}
        self.assertEqual(compare_path([sample(x)]*2,[sample(x)]*2)[0],"unobserved")

    def test_insufficient_observations(self):
        self.assertEqual(compare_path([],[])[0],"inconclusive")
        self.assertEqual(compare_path([sample()],[sample()])[0],"inconclusive")

    def test_invalid_settings(self):
        for cfg in [Settings(depth=True),Settings(budget=3.5)]:
            with self.assertRaises(ValueError): cfg.validate()

    def test_invalid_urls(self):
        for url in ["http://@localhost","http://localhost\n","http://localhost:bad"]:
            with self.assertRaises(ValueError): validate_url(url)
