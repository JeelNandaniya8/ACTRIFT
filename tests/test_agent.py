import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ghostdiff.agent import summarize
from ghostdiff.cli import main

def fixture():
    return {"schema":"ghostdiff.evidence/v1","observation_revision":3,
            "before_url":"http://127.0.0.1:3000/secret",
            "paths":[{"status":"inventory","path":[]},{"status":"equivalent_observed","path":[{"role":"button","name":"private action"}]},{"status":"behavior_changed","path":[{"role":"button","name":"private label"}],"reason":"private error"}],
            "summary":{"inventory":1,"equivalent_observed":1,"behavior_changed":1},
            "coverage":{"executed_paths":3,"omitted_budget_branches":0},
            "baseline_only_actions":[],"candidate_only_actions":[],"skipped_actions":[]}

class AgentTests(unittest.TestCase):
    def test_data_minimization_and_verdict(self):
        report=fixture();result=summarize(report)
        self.assertEqual(result["exit_code"],1)
        self.assertEqual(result["findings"],[{"evidence_index":2,"status":"behavior_changed","depth":1}])
        self.assertNotIn("private",json.dumps(result))
        self.assertNotIn("127.0.0.1",json.dumps(result))
        report["summary"]["behavior_changed"]=0
        with self.assertRaises(ValueError):summarize(report)
    def test_incomplete_scope(self):
        report=fixture();report["paths"].pop();report["summary"].pop("behavior_changed");report["coverage"]["executed_paths"]=2
        report["coverage"]["omitted_budget_branches"]=1
        self.assertEqual(summarize(report)["exit_code"],0)
        self.assertEqual(summarize(report,True)["exit_code"],2)
    def test_cli_authorization_and_json(self):
        cfg={"schema":"ghostdiff.config/v1","before":"http://127.0.0.1:3000","after":"http://127.0.0.1:3001","settings":{},"bidirectional":False,"strict":False}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"config.json";p.write_text(json.dumps(cfg),encoding="utf-8")
            output=io.StringIO()
            with patch("ghostdiff.cli.compare") as compare,redirect_stdout(output):
                self.assertEqual(main(["agent-run",str(p)]),2)
                compare.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())["execution_status"],"error")
            output=io.StringIO()
            with patch("ghostdiff.cli.compare",return_value=fixture()) as compare,redirect_stdout(output):
                self.assertEqual(main(["agent-run",str(p),"--allow-actions"]),1)
                compare.assert_called_once()
            self.assertEqual(json.loads(output.getvalue())["verdict"],"differences_observed")
            evidence=Path(d)/"evidence.json";evidence.write_text(json.dumps(fixture()),encoding="utf-8")
            output=io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["agent-summary",str(evidence)]),1)
            self.assertNotIn("private",output.getvalue())
