import copy
import unittest
from ghostdiff.history import timeline
from test_intelligence import row,evidence

class HistoryTests(unittest.TestCase):
    def test_scope_changes(self):
        a=evidence("a","b",[row("Save")]);b=copy.deepcopy(a);c=evidence("a","b",[row("Save","Changed")])
        d=evidence("a","b",[row("Export")])
        result=timeline([(k,e,"before") for k,e in zip(("a","b","c","d"),(a,b,c,d))])
        self.assertEqual([x["status"] for x in result["revisions"]],["initial","same_observed_digest","changed_observed_digest","different_scope"])
        with self.assertRaises(ValueError):timeline([("a",a,"before"),("a",b,"before")])
