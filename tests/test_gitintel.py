import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from ghostdiff.gitintel import revisions,assets,git_bisect
from ghostdiff.sourceintel import changed_hunks,rank_hunks
from ghostdiff.engine import Settings

class GitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        def git(*args):
            return subprocess.check_output(["git","-C",str(self.root),*args],stderr=subprocess.DEVNULL).decode().strip()
        self.git=git
        git("init");git("config","user.name","Fixture");git("config","user.email","fixture@example.invalid")
        (self.root/"site").mkdir()
        self.shas=[]
        for index,output in enumerate(("Done","Done","Broken","Broken")):
            (self.root/"site"/"index.html").write_text(f"""<!doctype html><html><body><button onclick="document.querySelector('p').textContent='{output}'">Export</button><p>Ready</p><!-- {index} --></body></html>""",encoding="utf-8")
            git("add","site");git("commit","-m",f"fixture {index}");self.shas.append(git("rev-parse","HEAD"))

    def test_git_history_and_source(self):
        self.assertEqual(revisions(self.root,self.shas[0],self.shas[-1]),self.shas)
        self.assertIn(b"Broken",assets(self.root,self.shas[2],"site")["index.html"])
        with self.assertRaises(ValueError):assets(self.root,self.shas[0],"../site")
        hunks=changed_hunks(self.root,self.shas[1],self.shas[2])
        result=rank_hunks(hunks,{"action":{"name":"Export"}})
        self.assertEqual(result[0]["file"],"site/index.html")
        self.assertEqual(result[0]["line"],1)

    @unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
    def test_automatic_git_bisect(self):
        head=self.git("rev-parse","HEAD")
        result=git_bisect(self.root,self.shas[0],self.shas[-1],"site",exhaustive=True,cfg=Settings(depth=1,budget=3,settle_ms=100))
        self.assertEqual(result["status"],"observed_boundary")
        self.assertEqual(result["boundary"]["first_bad"],self.shas[2])
        self.assertEqual(self.git("rev-parse","HEAD"),head)
        self.assertEqual(self.git("status","--porcelain"),"")
