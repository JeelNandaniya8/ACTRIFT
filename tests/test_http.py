"""Exercise failures that leave the rendered UI unchanged."""
import os
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from ghostdiff.engine import Settings,compare,http_failure
from ghostdiff.contracts import freeze

@contextmanager
def fixture(status):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api?"):
                code,body=status,b""
            elif self.path=="/":
                code,body=200,b"""<html><body><button onclick="fetch('/api?fixture=private').catch(()=>{})">Refresh</button><button onclick="document.querySelector('p').textContent='Saved'">Save note</button><p>Ready</p></body></html>"""
            else:
                code,body=404,b""
            self.send_response(code)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield f"http://127.0.0.1:{server.server_port}/"
    finally: server.shutdown();server.server_close();thread.join()

class HttpTests(unittest.TestCase):
    def test_policy(self):
        self.assertTrue(http_failure("document",404))
        self.assertTrue(http_failure("fetch",503))
        self.assertTrue(http_failure("xhr",500))
        self.assertFalse(http_failure("fetch",404))
        self.assertFalse(http_failure("image",404))
        self.assertFalse(http_failure("document",200))

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class BrowserHttpTests(unittest.TestCase):
    def test_hidden_server_failure(self):
        with fixture(200) as good,fixture(503) as bad:
            cfg=Settings(depth=1,budget=5,settle_ms=400)
            report=compare(good,bad,cfg)
            reverse=compare(bad,good,cfg)
        def row(data):
            return next(x for x in data["paths"] if x["path"]==[{"role":"button","name":"Refresh"}])
        self.assertEqual(row(report)["status"],"behavior_changed")
        self.assertEqual(row(report)["after"][0]["steps"][0]["outcome"]["http_errors"],[{"resource":"fetch","status":503,"path":"/api"}])
        self.assertEqual(row(reverse)["status"],"inconclusive")
        self.assertNotIn([{"role":"button","name":"Refresh"}],[x["path"] for x in freeze(reverse)["contracts"]])
