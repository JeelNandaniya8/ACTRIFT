import os
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from ghostdiff.api_observe import json_digest,validate_paths
from ghostdiff.engine import Settings,compare

class ApiTests(unittest.TestCase):
    def test_json_and_policy(self):
        self.assertEqual(json_digest(b'{"a":1,"b":2}'),json_digest(b'{ "b":2, "a":1 }'))
        self.assertNotEqual(json_digest(b'{"a":1}'),json_digest(b'{"a":2}'))
        for data in (b'{"a":1,"a":2}',b'NaN',b'x'*65537):
            with self.assertRaises(ValueError):json_digest(data)
        for paths in (["/api?q=1"],["//host"],["/a/../b"],["/x","/x"]):
            with self.assertRaises(ValueError):validate_paths(paths)

@contextmanager
def fixture(body,delay=0):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                data=b"""<html><body><button onclick="fetch('/api?fixture=hidden').then(r=>r.json())">Refresh</button><p>Ready</p></body></html>""";kind="text/html"
            elif self.path.startswith("/api?"):
                data=body;kind="application/json"
            else:
                self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(data)));self.end_headers()
            if self.path.startswith('/api?') and delay:
                from time import sleep
                sleep(delay)
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/"
    finally:server.shutdown();server.server_close();thread.join()

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class ApiBrowserTests(unittest.TestCase):
    def test_hidden_json_change(self):
        with fixture(b'{"value":1,"label":"private-fixture"}') as a,fixture(b'{"label":"private-fixture","value":1}') as b,fixture(b'{"value":2,"label":"private-fixture"}') as c:
            cfg=Settings(depth=1,budget=2,settle_ms=300,api_paths=("/api",))
            good=compare(a,b,cfg);bad=compare(a,c,cfg)
        self.assertEqual(good["summary"].get("equivalent_observed"),1)
        self.assertEqual(bad["summary"].get("behavior_changed"),1)
        import json
        self.assertNotIn("private-fixture",json.dumps(bad))
        self.assertNotIn("fixture=hidden",json.dumps(bad))

    def test_unfinished_selected_response_is_inconclusive(self):
        with fixture(b'{"value":1}') as a,fixture(b'{"value":1}',delay=2) as b:
            cfg=Settings(depth=1,budget=2,settle_ms=100,api_paths=("/api",))
            result=compare(a,b,cfg)
        self.assertEqual(result["summary"].get("inconclusive"),1)
        self.assertNotIn("equivalent_observed",result["summary"])
