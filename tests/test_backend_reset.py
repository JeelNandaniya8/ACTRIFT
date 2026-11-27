import os
import sqlite3
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread,Lock
from ghostdiff.reset import reset_backend,reset_target
from ghostdiff.engine import compare,Settings
from ghostdiff.contracts import freeze

@contextmanager
def fixture(increment=1,status=204):
    db=sqlite3.connect(":memory:",check_same_thread=False)
    db.execute("create table counter(value integer)")
    db.execute("insert into counter values(0)")
    db.commit()
    lock=Lock()
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.path)
            if self.path!="/_ghostdiff/reset":
                self.send_error(404);return
            if status==204:
                with lock:
                    db.execute("update counter set value=0");db.commit()
            self.send_response(status)
            if status==302:self.send_header("Location","/unexpected")
            self.send_header("Content-Length","0");self.end_headers()
        def do_GET(self):
            if self.path=="/":
                body=b"""<!doctype html><html><body><button onclick="fetch('/increment').then(r=>r.text()).then(v=>document.querySelector('p').textContent=v)">Increment</button><p>Ready</p></body></html>"""
            elif self.path=="/increment":
                with lock:
                    db.execute("update counter set value=value+?",(increment,));db.commit()
                    body=str(db.execute("select value from counter").fetchone()[0]).encode()
            else:
                received.append(self.path);self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type","text/html" if self.path=="/" else "text/plain")
            self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/",received
    finally:server.shutdown();server.server_close();thread.join();db.close()

class ResetPolicyTests(unittest.TestCase):
    def test_reject_remote_or_ambiguous_target(self):
        for url in ("http://localhost:3000","https://127.0.0.1:3000","http://127.0.0.1","http://example.com:3000","http://user@127.0.0.1:3000"):
            with self.assertRaises(ValueError):reset_target(url)
        self.assertEqual(reset_target("http://127.0.0.1:3000/"),("127.0.0.1",3000))

    def test_redirect_not_followed(self):
        with fixture(status=302) as (url,received):
            self.assertFalse(reset_backend(url))
            self.assertEqual(received,["/_ghostdiff/reset"])

    def test_explicit_authorization_and_separate_targets(self):
        with self.assertRaises(ValueError):
            compare("http://127.0.0.1:3000","http://127.0.0.1:3000",Settings(),reset=True)

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BackendResetTests(unittest.TestCase):
    def test_stateful_database_regression(self):
        cfg=Settings(depth=1,budget=2,settle_ms=200)
        with fixture() as (a,ar),fixture() as (b,br),fixture(2) as (c,cr):
            unstable=compare(a,b,cfg)
            self.assertEqual(unstable["summary"].get("inconclusive"),1)
            self.assertEqual(ar+br,[])
            clean=compare(a,b,cfg,reset=True)
            broken=compare(a,c,cfg,reset=True)
            self.assertEqual(clean["summary"].get("equivalent_observed"),1)
            self.assertEqual(broken["summary"].get("behavior_changed"),1)
            self.assertTrue(clean["backend_reset"])
            self.assertEqual(len(br),4)
            self.assertEqual(len(cr),4)
            with self.assertRaises(ValueError):freeze(clean)

    def test_failed_reset_never_verifies(self):
        with fixture() as (a,_),fixture(status=500) as (b,_):
            result=compare(a,b,Settings(depth=1,budget=2,settle_ms=100),reset=True)
            self.assertNotIn("equivalent_observed",result["summary"])
            self.assertGreater(result["summary"].get("inconclusive",0),0)
