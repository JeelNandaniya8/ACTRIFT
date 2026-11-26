
import os
import tempfile
from pathlib import Path
import unittest
from ghostdiff.engine import Action,Settings,compare,ignored
from ghostdiff.demo import serve
from ghostdiff.cli import report_html

class PolicyTests(unittest.TestCase):
    def test_risky_and_custom_names(self):
        self.assertTrue(ignored(Action("button","Delete account"),Settings()))
        self.assertTrue(ignored(Action("link","Sign out"),Settings()))
        self.assertFalse(ignored(Action("button","Export PDF"),Settings()))
        self.assertTrue(ignored(Action("button","Refresh"),Settings(ignore=(" refresh ",))))
        self.assertFalse(ignored(Action("button","Delete account"),Settings(allow_risky_actions=True)))
    def test_invalid_rules(self):
        for cfg in (Settings(mask_text="body"),Settings(ignore=("",))):
            with self.assertRaises(ValueError):cfg.validate()

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BrowserPolicyTests(unittest.TestCase):
    def test_ignore_mask_and_screenshot(self):
        template=b"""<html><body><button onclick="document.querySelector('#out').innerText='saved';document.querySelector('.timestamp').innerText='TIME'">Save note</button><button onclick="document.body.innerText='deleted'">Delete account</button><p id="out">draft</p><p class="timestamp">initial</p></body></html>"""
        with serve(template.replace(b"TIME",b"today")) as a,serve(template.replace(b"TIME",b"tomorrow")) as b:
            report=compare(a,b,Settings(depth=1,budget=6,mask_text=(".timestamp",),screenshots=True))
        rows={tuple(x["name"] for x in r["path"]):r for r in report["paths"]}
        self.assertNotIn(("Delete account",),rows)
        self.assertEqual(rows[("Save note",)]["status"],"equivalent_observed")
        self.assertTrue(report["skipped_actions"])
        self.assertIn("data:image/jpeg;base64,",report_html(report))
    def test_test_account_storage(self):
        import json
        from ghostdiff.contracts import freeze,verify
        # Use a simple script without interpolating real credentials.
        html=b"""<html><body><button id="save" hidden>Save note</button><p id="out">draft</p><script>if(localStorage.getItem('testSession')==='fixture'){document.querySelector('#save').hidden=false;document.querySelector('#save').onclick=()=>document.querySelector('#out').textContent='saved'}</script></body></html>"""
        with serve(html) as a,serve(html) as b,tempfile.TemporaryDirectory() as d:
            def state(url,name):
                p=Path(d)/name
                p.write_text(json.dumps({"cookies":[],"origins":[{"origin":url.rstrip("/"),"localStorage":[{"name":"testSession","value":"fixture"}]}]}))
                return str(p)
            x,y=state(a,"a.json"),state(b,"b.json")
            report=compare(a,b,Settings(depth=1,budget=6),x,y)
            data=freeze(report)
            self.assertTrue(data["authenticated"])
            self.assertNotIn(x,json.dumps(report))
            with self.assertRaises(ValueError):verify(data,b)
            self.assertEqual(verify(data,b,storage_state=y)["summary"],{"matched":1})
