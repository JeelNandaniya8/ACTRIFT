import json
import tempfile
import unittest
from pathlib import Path
from benchmarks.ghostbench import summarize,SUITES

class GhostbenchTests(unittest.TestCase):
    def test_requires_every_report(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(summarize(d,"core")["passed"])
            for name in SUITES["core"]:
                (Path(d)/name).write_text(json.dumps({"passed":True}),encoding="utf-8")
            self.assertTrue(summarize(d,"core")["passed"])
            (Path(d)/"benchmark.json").write_text('{"passed":"true"}',encoding="utf-8")
            self.assertFalse(summarize(d,"core")["passed"])
