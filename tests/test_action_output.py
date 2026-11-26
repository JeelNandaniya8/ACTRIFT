import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"action_output.py"

class OutputTests(unittest.TestCase):
    def test_missing_report(self):
        with tempfile.TemporaryDirectory() as d:
            out=subprocess.check_output([sys.executable,str(SCRIPT),str(Path(d)/"absent.json")],text=True)
        self.assertEqual(out.strip(),"summary=No complete report")
    def test_only_fixed_labels(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"evidence.json"
            p.write_text(json.dumps({"summary":{"unmatched":2,"application text":999},"secret":"not included"}),encoding="utf-8")
            out=subprocess.check_output([sys.executable,str(SCRIPT),str(p)],text=True)
        self.assertIn("unmatched: 2",out)
        self.assertNotIn("application text",out)
        self.assertNotIn("not included",out)
