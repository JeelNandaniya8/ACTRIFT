"""Defensive regression tests; not a penetration test or independent audit."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import os
import unittest
from ghostdiff.engine import Settings,compare
from ghostdiff.cli import report_html
from ghostdiff.observatory import render_observatory

@contextmanager
def fixture(body):
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                data=body
            else:
                received.append(("GET",self.path))
                data=b""
            self.send_response(200);self.send_header("Content-Type","text/html");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            received.append(("POST",self.path))
            self.send_response(200);self.send_header("Content-Length","0");self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/",received
    finally:server.shutdown();server.server_close();thread.join()

class SecurityReportTests(unittest.TestCase):
    def test_html_escapes_evidence(self):
        payload='<img src=x onerror=alert(1)>'
        report={"before_url":"http://localhost/","after_url":"http://localhost/","summary":{"inventory":1},"paths":[{"path":[],"status":"inventory","reason":payload,"before":[{"initial":{"text":[payload]}}],"after":[]}],"limits":payload}
        for html in (report_html(report),render_observatory(report)):
            self.assertNotIn(payload,html)
            self.assertIn("&lt;img",html)

@unittest.skipUnless(os.environ.get("GHOSTDIFF_BROWSER_TESTS")=="1","requires browser")
class NetworkPolicyTests(unittest.TestCase):
    def test_default_post_is_blocked(self):
        body=b"""<html><body><button onclick="fetch('/mutation',{method:'POST'}).catch(()=>{})">Attempt operation</button></body></html>"""
        with fixture(body) as (a,ar),fixture(body) as (b,br):
            result=compare(a,b,Settings(depth=1,budget=3,settle_ms=200))
            self.assertNotIn(("POST","/mutation"),ar+br)
        self.assertEqual(result["summary"].get("inconclusive"),1)

    def test_off_origin_request_is_blocked(self):
        with fixture(b"unused") as (destination,received):
            body=("<html><body><button onclick=\"fetch('"+destination+"probe').catch(()=>{})\">Attempt operation</button></body></html>").encode()
            with fixture(body) as (a,_),fixture(body) as (b,_):
                result=compare(a,b,Settings(depth=1,budget=3,settle_ms=200))
            self.assertNotIn(("GET","/probe"),received)
        self.assertEqual(result["summary"].get("inconclusive"),1)
