import base64
import json
import tempfile
import unittest
from pathlib import Path
from ghostdiff.static_bundle import SCHEMA,MAX_FILE,pack_site,parse_bundle,decode_site

def encode(data):
    return base64.b64encode(data).decode("ascii")

class StaticBundleTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"index.html").write_bytes(b"<p>Ready</p>")
            (p/"assets").mkdir()
            (p/"assets"/"app.js").write_bytes(b"console.log(1)")
            packed=pack_site(p)
            before,after=parse_bundle(json.dumps({"schema":SCHEMA,"before":packed,"after":packed}).encode())
            self.assertEqual(before,after)
            self.assertEqual(before["assets/app.js"],b"console.log(1)")

    def test_unsafe_inventory(self):
        for name in ("../private.txt","/root.html",".env","assets/.secret.json","a\\b.js","secrets.pem","a/../x.js","a//b.js"):
            with self.subTest(name=name),self.assertRaises(ValueError):
                decode_site({"index.html":encode(b"ok"),name:encode(b"bad")})
        with self.assertRaises(ValueError):decode_site({"index.html":"not-base64"})
        with self.assertRaises(ValueError):decode_site({"index.html":encode(b"x"*(MAX_FILE+1))})
        with self.assertRaises(ValueError):parse_bundle(b'{"schema":"ghostdiff.static-bundle/v1","schema":"duplicate","before":{},"after":{}}')

    def test_hidden_and_symlink_packing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"index.html").write_text("ok",encoding="utf-8")
            (p/".env").write_text("private",encoding="utf-8")
            with self.assertRaises(ValueError):pack_site(p)
            (p/".env").unlink()
            try:(p/"alias.html").symlink_to(p/"index.html")
            except (OSError,NotImplementedError):self.skipTest("Symlink creation not available")
            with self.assertRaises(ValueError):pack_site(p)
