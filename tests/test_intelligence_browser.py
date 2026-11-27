import os
import unittest
from contextlib import ExitStack
from ghostdiff.demo import serve
from ghostdiff.engine import compare,Settings
from ghostdiff.contracts import freeze
from ghostdiff.intelligence import fingerprint,match_renames
from ghostdiff.diagnostics import diagnose
from ghostdiff.bisect import bisect

def app(name="Export",output="Done"):
    return f"""<!doctype html><html><body><button onclick="document.querySelector('p').textContent='{output}'">{name}</button><p>Ready</p></body></html>""".encode()

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BrowserIntelligence(unittest.TestCase):
    def test_rename_fingerprint_diagnostic_and_bisect(self):
        cfg=Settings(depth=1,budget=3,settle_ms=100)
        with ExitStack() as stack:
            urls=[stack.enter_context(serve(app(output=out))) for out in ("Done","Done","Broken","Broken")]
            renamed=stack.enter_context(serve(app(name="Download")))
            good=compare(urls[0],urls[1],cfg)
            bad=compare(urls[0],urls[2],cfg)
            self.assertEqual(fingerprint(good)["behavior_sha256"],fingerprint(good,"after")["behavior_sha256"])
            self.assertNotEqual(fingerprint(bad)["behavior_sha256"],fingerprint(bad,"after")["behavior_sha256"])
            forward=compare(urls[0],renamed,cfg);reverse=compare(renamed,urls[0],cfg)
            result=match_renames(forward,reverse)["hypotheses"]
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]["status"],"review_required")
            self.assertEqual(result[0]["candidates"][0]["name"],"Download")
            self.assertEqual(diagnose(bad)["findings"][0]["first_observed_divergence"]["step"],1)
            manifest={"schema":"ghostdiff.revisions/v1","revisions":[{"commit":f"{i:040x}","url":url} for i,url in enumerate(urls,1)]}
            result=bisect(manifest,freeze(good),exhaustive=True)
            self.assertEqual(result["status"],"observed_boundary")
            self.assertEqual(result["boundary"]["first_bad"],manifest["revisions"][2]["commit"])
