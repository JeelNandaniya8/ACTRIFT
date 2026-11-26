"""Small independent smoke matrix for non-default browser engines."""
import os
import unittest
from ghostdiff.demo import app, serve
from ghostdiff.engine import Settings, compare

ENGINE=os.environ.get("GHOSTDIFF_CROSS_BROWSER")

@unittest.skipUnless(ENGINE in ("firefox","webkit"),"requires explicit browser matrix")
class CrossBrowserTests(unittest.TestCase):
    def test_observable_journeys(self):
        cfg=Settings(browser=ENGINE,depth=1,budget=8,settle_ms=300,timeout_ms=6000)
        with serve(app()) as a,serve(app(broken=True)) as b,serve(app(redesign=True)) as c:
            changed=compare(a,b,cfg)
            clean=compare(a,c,cfg)
        rows={tuple(x["name"] for x in row["path"]):row["status"] for row in changed["paths"]}
        self.assertEqual(rows.get(("Search history",)),"unmatched")
        self.assertEqual(rows.get(("Export PDF",)),"download_changed")
        self.assertGreater(clean["summary"].get("equivalent_observed",0),0)
        self.assertLessEqual(set(clean["summary"]),{"inventory","equivalent_observed","unobserved"})
