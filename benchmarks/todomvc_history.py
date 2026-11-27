"""Pinned TodoMVC VanillaJS application historical regression and clean control."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from ghostdiff.engine import Action,Settings,replay

ROOT=Path(__file__).parent/"historical"/"todomvc"
ASSETS={str(p.relative_to(ROOT/"app")):p.read_bytes() for p in (ROOT/"app").rglob("*") if p.is_file()}

@contextmanager
def fixture(broken=False):
    assets=dict(ASSETS)
    if broken: assets["js/controller.js"]=(ROOT/"buggy-controller.js").read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlsplit(self.path).path.lstrip("/") or "index.html"
            data=assets.get(path)
            if data is None:
                self.send_error(404);return
            kind="text/javascript" if path.endswith(".js") else "text/css" if path.endswith(".css") else "text/html"
            self.send_response(200);self.send_header("Content-Type",kind+"; charset=utf-8")
            self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/"
    finally:server.shutdown();server.server_close();thread.join()

def state(url):
    data={"todos":[{"id":1,"title":"Active task","completed":0},{"id":2,"title":"Completed task","completed":1}]}
    return {"cookies":[],"origins":[{"origin":url.rstrip("/"),"localStorage":[{"name":"todos-vanillajs","value":json.dumps(data)}]}]}

def run():
    cfg=Settings(depth=2,settle_ms=500)
    path=(Action("link","Active"),Action("button","Clear completed (1)"))
    with fixture() as a,fixture(True) as b,fixture() as c:
        report=replay(a,b,path,cfg,state(a),state(b))
        control=replay(a,c,path,cfg,state(a),state(c))
    errors=[err for run in report["after"] for step in run.get("steps",[]) for err in step["outcome"].get("page_errors",[])]
    return {"kind":"historical multi-file reference application","buggy":"22587178cbae854290413e68faa6627a7a64677a","fixed":"1e0e19087fd48bf48a37a742ef4e550019964619","observed":report["status"],"clean_control":control["status"],"errors":errors,"passed":report["status"]=="behavior_changed" and len(errors)>=2 and control["status"]=="equivalent_observed","evidence":report,"control_evidence":control}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="todomvc-history.json");a=p.parse_args()
    r=run()
    Path(a.out).write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k not in ("evidence","control_evidence")},indent=2))
    raise SystemExit(0 if r["passed"] else 1)
