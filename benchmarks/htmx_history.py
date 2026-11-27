"""Pinned htmx out-of-band swap regression with actual local HTTP response."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import json
from pathlib import Path
from ghostdiff.engine import Action,Settings,replay

ROOT=Path(__file__).parent/"historical"/"htmx"
HTML=b"""<!doctype html><html><head><script src="/htmx.js"></script></head><body><button hx-get="/test" hx-target="#main">Refresh</button><div id="main">Ready</div><div id="foo-/bar/">Existing content</div></body></html>"""
RESPONSE=b'<div id="foo-/bar/" hx-swap-oob="innerHTML">Updated content</div><p>Response received</p>'

@contextmanager
def fixture(name,root=ROOT,html=HTML,response=RESPONSE):
    assets={"/":("text/html",html),"/htmx.js":("text/javascript",(root/(name+".js")).read_bytes()),"/test":("text/html",response)}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            entry=assets.get(self.path)
            if entry is None:self.send_error(404);return
            kind,body=entry
            self.send_response(200);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/"
    finally:server.shutdown();server.server_close();thread.join()

def run():
    path=(Action("button","Refresh"),);cfg=Settings(depth=1,settle_ms=600)
    with fixture("fixed") as a,fixture("buggy") as b,fixture("fixed") as c:
        result=replay(a,b,path,cfg);control=replay(a,c,path,cfg)
    expected=all("Updated content" in r.get("final",{}).get("text",[]) for r in result["before"])
    missing=all("Updated content" not in r.get("final",{}).get("text",[]) for r in result["after"])
    return {"kind":"historical upstream library regression","fixed":"730bd8224da11628bdd9363baf114325fa30a3b5","buggy":"8409ebca3bad8d67b3f6bcd71bbe614888a73da0","observed":result["status"],"clean_control":control["status"],"passed":expected and missing and result["status"]=="behavior_changed" and control["status"]=="equivalent_observed","evidence":result,"control_evidence":control}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="htmx-history.json");a=p.parse_args()
    r=run();Path(a.out).write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k not in ("evidence","control_evidence")},indent=2));raise SystemExit(0 if r["passed"] else 1)
