import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ghostdiff.build_artifacts import pack_artifact,parse_manifest,load_artifact,build_bisect
from ghostdiff.engine import Settings

class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows=[]
        for i,value in enumerate(("Done","Done","Broken","Broken")):
            site=self.root/("dist"+str(i));site.mkdir()
            (site/"index.html").write_text("<!doctype html><script src='app.js'></script><button onclick='run()'>Export</button><p>Ready</p>",encoding="utf-8")
            # Mimic a generated build asset rather than committing browser-ready source.
            (site/"app.js").write_text("function run(){document.querySelector('p').textContent="+json.dumps(value)+"}",encoding="utf-8")
            self.rows.append(pack_artifact(site,format(i+1,"040x"),self.root/("build"+str(i)+".json")))
        self.manifest=self.root/"manifest.json";self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps({"schema":"ghostdiff.build-revisions/v1","revisions":self.rows}),encoding="utf-8")

    def test_integrity_and_no_overwrite(self):
        root,rows=parse_manifest(self.manifest)
        self.assertIn(b"Broken",load_artifact(root,rows[2])["app.js"])
        with self.assertRaises(FileExistsError):
            pack_artifact(self.root/"dist0",rows[0]["commit"],root/rows[0]["artifact"])
        target=root/rows[0]["artifact"];target.write_bytes(target.read_bytes()+b" ")
        with patch("ghostdiff.build_artifacts.compare") as compare:
            with self.assertRaisesRegex(ValueError,"checksum mismatch"):build_bisect(self.manifest)
            compare.assert_not_called()

    def test_path_and_commit_validation(self):
        self.rows[0]["artifact"]="../secret.json";self.write_manifest()
        with self.assertRaises(ValueError):parse_manifest(self.manifest)
        self.rows[0]["artifact"]="build0.json"
        self.rows[0]["commit"]="f"*40;self.write_manifest()
        root,rows=parse_manifest(self.manifest)
        with self.assertRaisesRegex(ValueError,"commit label mismatch"):load_artifact(root,rows[0])

    @unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
    def test_artifact_boundary(self):
        result=build_bisect(self.manifest,exhaustive=True,cfg=Settings(depth=1,budget=3,settle_ms=100))
        self.assertEqual(result["status"],"observed_boundary")
        self.assertEqual(result["boundary"]["first_bad"],self.rows[2]["commit"])
        self.assertEqual(len(result["tested"]),4)
