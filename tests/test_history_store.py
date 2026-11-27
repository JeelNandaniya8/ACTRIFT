import tempfile
import unittest
from pathlib import Path
from ghostdiff.history_store import record,history
from test_intelligence import row,evidence

class StoreTests(unittest.TestCase):
    def test_append_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"history.db"
            a=evidence("a","b",[row("Save")]);b=evidence("a","b",[row("Save","Changed")]);c=evidence("a","b",[row("Export")])
            for key,value in zip(("v1","v2","v3"),(a,b,c)):record(db,"demo",key,value)
            self.assertEqual([r["status"] for r in history(db,"demo")["captures"]],["initial_in_window","changed_observed_digest","different_scope"])
            with self.assertRaises(ValueError):record(db,"demo","v1",a)
            self.assertEqual(history(db,"other")["captures"],[])
            self.assertNotIn(b"Save",db.read_bytes())
