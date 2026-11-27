"""Exercise a historical missing-MessagePort fix with a separate test driver."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from ghostdiff.engine import Settings,compare

ROOT=Path(__file__).parent/"historical"/"mdn-channel"
HARNESS=b"""<!doctype html><html><body><iframe id="child" src="/page2.html"></iframe><button id="test">Test message without port</button><p id="out">Ready</p><script>document.getElementById('test').onclick=()=>{document.getElementById('child').contentWindow.postMessage('fixture message',location.origin);document.getElementById('out').textContent='Message delivered to browser';};</script></body></html>"""

@contextmanager
def serve_revision(name):
    child=(ROOT/(name+".html")).read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data={"/":HARNESS,"/page2.html":child}.get(self.path)
            if data is None:
                self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/"
    finally:server.shutdown();server.server_close();thread.join()

def run():
    cfg=Settings(depth=1,budget=4,settle_ms=400)
    with serve_revision("fixed") as a,serve_revision("buggy") as b,serve_revision("fixed") as c:
        report=compare(a,b,cfg)
        control=compare(a,c,cfg)
    def row(data):
        return next(r for r in data["paths"] if r["path"]==[{"role":"button","name":"Test message without port"}])
    change=row(report)
    errors=[e for r in change["after"] for s in r.get("steps",[]) for e in s["outcome"].get("page_errors",[])]
    clean=row(control)["status"]
    return {"kind":"historical upstream example defect with separate harness","fixed":"98c8bb8b20e627161b0cf2cc17a1fccd2258f79b","buggy":"36eba9f807f24dab86745e7b1634c97865ec2594","observed":change["status"],"errors":errors,"clean_control":clean,"passed":change["status"]=="behavior_changed" and len(errors)>=2 and clean=="equivalent_observed","evidence":report}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="channel-history.json");a=p.parse_args()
    result=run()
    Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="evidence"},indent=2))
    raise SystemExit(0 if result["passed"] else 1)
