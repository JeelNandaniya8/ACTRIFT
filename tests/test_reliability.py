"""Regression guards for unhealthy baselines and escaped interactive reports."""
import unittest
from ghostdiff.engine import compare_path
from ghostdiff.observatory import render_observatory
from test_intelligence import row,evidence

class ReliabilityTests(unittest.TestCase):
    def test_unhealthy_baseline_before_unmatched(self):
        r=row("Export")
        before=r["before"]
        for run in before:
            run["steps"][0]["outcome"]["http_errors"]=[{"path":"/api","status":503}]
        after=[{"status":"unmatched","at":0,"steps":[]} for _ in range(2)]
        self.assertEqual(compare_path(before,after)[0],"inconclusive")

    def test_observatory_filters_and_escape(self):
        data=evidence("a","b",[row('Export " <script>alert(1)</script>')])
        data.update(summary={"inventory":1,"equivalent_observed":1},limits="test",coverage={"executed_paths":2})
        rendered=render_observatory(data)
        self.assertIn('id="search"',rendered)
        self.assertIn('id="filter"',rendered)
        self.assertIn("Coverage and execution",rendered)
        self.assertNotIn("<script>alert(1)</script>",rendered)
        self.assertIn("&lt;script&gt;",rendered)
