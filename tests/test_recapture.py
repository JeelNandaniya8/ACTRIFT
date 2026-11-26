import copy
import os
import unittest
from dataclasses import asdict
from ghostdiff.contracts import freeze, recapture, validate_aliases, verify
from ghostdiff.engine import Action, Settings, compare
from ghostdiff.demo import app,serve

class AliasTests(unittest.TestCase):
    def setUp(self):
        self.contracts=[{"id":"one","path":[{"role":"button","name":"Export PDF"}]}]
        self.alias={"schema":"ghostdiff.aliases/v1","aliases":[{"contract_id":"one","step":0,"from":"Export PDF","to":"Download PDF"}]}
    def test_explicit_mapping(self):
        self.assertEqual(validate_aliases(self.alias,self.contracts),{("one",0):Action("button","Download PDF")})
    def test_unknown_and_duplicate_rejected(self):
        for changes in [{"contract_id":"other"},{"step":-1},{"from":"Delete"},{"step":True}]:
            alias=copy.deepcopy(self.alias); alias["aliases"][0].update(changes)
            with self.assertRaises(ValueError): validate_aliases(alias,self.contracts)
        self.alias["aliases"]*=2
        with self.assertRaises(ValueError): validate_aliases(self.alias,self.contracts)

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class RecaptureTests(unittest.TestCase):
    def test_legacy_roundtrip_and_rejection(self):
        with serve(app()) as a,serve(app(broken=True)) as b:
            evidence=compare(a,b,Settings(depth=1,budget=8,settle_ms=150))
            fresh=freeze(evidence)
            legacy=copy.deepcopy(fresh)
            legacy["observation_revision"]=2
            for c in legacy["contracts"]:
                for outcome in c["expected"]: outcome.pop("page_errors",None)
            upgraded=recapture(legacy,a)
            self.assertEqual(upgraded["contracts"],fresh["contracts"])
            with self.assertRaises(ValueError): recapture(legacy,b)
            renamed=app().replace(b"Export PDF",b"Download PDF")
            with serve(renamed) as target:
                export=next(c for c in fresh["contracts"] if c["path"]==[{"role":"button","name":"Export PDF"}])
                only={**fresh,"contracts":[export]}
                alias={"schema":"ghostdiff.aliases/v1","aliases":[{"contract_id":export["id"],"step":0,"from":"Export PDF","to":"Download PDF"}]}
                self.assertEqual(verify(only,target)["summary"],{"changed":1})
                self.assertEqual(verify(only,target,aliases=alias)["summary"],{"matched":1})
