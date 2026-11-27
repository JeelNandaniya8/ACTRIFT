import copy
import os
import unittest
from ghostdiff.demo import serve
from ghostdiff.engine import Settings
from ghostdiff.scenario import parse_spec,run_journeys
from ghostdiff.session import local_storage_state

SPEC={"schema":"ghostdiff.journeys/v1","journeys":[{"name":"Search","steps":[{"action":"fill","name":"Query","value":"sample"},{"action":"click","role":"button","name":"Search"}]}]}

class ScenarioTests(unittest.TestCase):
    def test_parse(self):
        name,path,values=parse_spec(SPEC)[0]
        self.assertEqual(name,"Search")
        self.assertEqual(path[0].role,"textbox")
        self.assertEqual(values,{0:"sample"})
    def test_invalid(self):
        for value in [123,"x"*501]:
            spec=copy.deepcopy(SPEC);spec["journeys"][0]["steps"][0]["value"]=value
            with self.assertRaises(ValueError):parse_spec(spec)
    def test_origin_scope(self):
        state={"cookies":[],"origins":[{"origin":"http://localhost:3001","localStorage":[]}]}
        with self.assertRaises(ValueError):local_storage_state(state,"http://localhost:3000")
        self.assertEqual(local_storage_state(state,"http://localhost:3001"),state)
        with self.assertRaises(ValueError):local_storage_state({"cookies":[{"domain":"example.com"}],"origins":[]},"http://localhost:3001")

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BrowserScenarioTests(unittest.TestCase):
    def test_explicit_form_regression(self):
        good=b"""<html><body><label>Query<input id="q"></label><button onclick="document.querySelector('p').textContent='Found: '+document.querySelector('#q').value">Search</button><p>Ready</p></body></html>"""
        bad=good.replace(b"'Found: '+document.querySelector('#q').value",b"'No results'")
        with serve(good) as a,serve(good) as b,serve(bad) as c:
            cfg=Settings(settle_ms=100)
            self.assertEqual(run_journeys(SPEC,a,b,cfg)["summary"],{"equivalent_observed":1})
            self.assertEqual(run_journeys(SPEC,a,c,cfg)["summary"],{"behavior_changed":1})
    def test_password_not_filled(self):
        html=b'<html><body><label>Password<input type="password"></label></body></html>'
        spec={"schema":"ghostdiff.journeys/v1","journeys":[{"name":"Blocked","steps":[{"action":"fill","name":"Password","value":"dummy"}]}]}
        with serve(html) as a,serve(html) as b:
            self.assertEqual(run_journeys(spec,a,b)["summary"],{"inconclusive":1})

    def test_native_searchbox(self):
        spec=copy.deepcopy(SPEC)
        spec["journeys"][0]["steps"][0]["role"]="searchbox"
        html=b"""<html><body><label>Query<input type="search" id="q"></label><button onclick="document.querySelector('p').textContent=document.querySelector('#q').value">Search</button><p>Ready</p></body></html>"""
        with serve(html) as a,serve(html) as b:
            self.assertEqual(run_journeys(spec,a,b,Settings(settle_ms=100))["summary"],{"equivalent_observed":1})
