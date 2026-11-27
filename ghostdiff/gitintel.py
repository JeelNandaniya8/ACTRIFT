"""Read-only Git history automation for trusted local static-site repositories."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,unquote
import mimetypes
import os
import re
import subprocess

from .bisect import locate
from .contracts import verify,freeze
from .engine import Settings,compare

SHA=re.compile(r"[0-9a-f]{40}")
MAX_ASSET=2*1024*1024
MAX_TOTAL=16*1024*1024

def git(repo,*args,limit=4*1024*1024):
    """Fixed argv, no shell; only use a trusted local repository and Git executable."""
    root=Path(repo).resolve(strict=True)
    if not root.is_dir():raise ValueError("Git repository must be a directory")
    env={k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT="0",GIT_NO_REPLACE_OBJECTS="1",GIT_OPTIONAL_LOCKS="0")
    try:
        p=subprocess.run(["git","-C",str(root),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Local Git command timed out") from exc
    if p.returncode:raise ValueError("Local Git command failed: "+args[0])
    if len(p.stdout)>limit:raise ValueError("Git output exceeds observation limit")
    return p.stdout

def commit(repo,sha):
    if not isinstance(sha,str) or not SHA.fullmatch(sha):raise ValueError("Provide full lowercase 40-character commit SHA")
    if git(repo,"rev-parse","--verify",sha+"^{commit}").decode().strip()!=sha:
        raise ValueError("Not an exact commit object")
    return sha

def revisions(repo,good,bad):
    commit(repo,good);commit(repo,bad)
    rows=git(repo,"rev-list","--first-parent","--max-count=65",bad).decode().splitlines()
    if good not in rows or rows.index(good)<1 or rows.index(good)>63:
        raise ValueError("Good must precede bad on its first-parent history within 64 revisions")
    return list(reversed(rows[:rows.index(good)+1]))

def site_prefix(site):
    if site==".":return ""
    p=PurePosixPath(site)
    if p.is_absolute() or any(x in (".","..") for x in site.split("/")) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,200}",site) or site.startswith("-"):
        raise ValueError("Use a safe repository-relative static site directory")
    return str(p).rstrip("/")+"/"

def assets(repo,sha,site):
    commit(repo,sha);prefix=site_prefix(site)
    entries=git(repo,"ls-tree","-r","-z","-l",sha,"--",prefix or ".",limit=2*1024*1024).split(b"\0")
    result={};total=0
    for entry in entries:
        if not entry:continue
        meta,path=entry.split(b"\t",1)
        mode,kind,oid,size=meta.decode("ascii").split()
        path=path.decode("utf-8")
        if prefix and not path.startswith(prefix):continue
        name=path[len(prefix):]
        if kind!="blob" or mode not in ("100644","100755"):
            raise ValueError("Static snapshots cannot contain symlinks or submodules")
        if not name or any(x in ("",".","..") for x in name.split("/")) or any(ord(c)<32 for c in name) or "\\" in name:
            raise ValueError("Unsupported static asset path")
        n=int(size);total+=n
        if n>MAX_ASSET or total>MAX_TOTAL or len(result)>=200:
            raise ValueError("Static snapshot exceeds 200 files, 2 MiB/file or 16 MiB total")
        body=git(repo,"cat-file","blob",oid,limit=MAX_ASSET)
        if len(body)!=n:raise ValueError("Unexpected Git blob size")
        result[name]=body
    if "index.html" not in result:raise ValueError("Static site must contain index.html")
    return result

@contextmanager
def serve_assets(files):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=unquote(urlsplit(self.path).path).lstrip("/")
            if not path or path.endswith("/"):path+="index.html"
            body=files.get(path)
            if body is None:
                self.send_error(404);return
            self.send_response(200)
            self.send_header("Content-Type",mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length",str(len(body)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}/"
    finally:server.shutdown();server.server_close();thread.join()

def git_bisect(repo,good,bad,site=".",contracts=None,exhaustive=False,cfg=None):
    ordered=revisions(repo,good,bad)
    if contracts is None:
        files=assets(repo,good,site)
        with serve_assets(files) as a,serve_assets(files) as b:
            contracts=freeze(compare(a,b,cfg or Settings(depth=1,budget=16)))
    if contracts.get("authenticated"):raise ValueError("Static Git automation does not support authenticated contracts")
    def probe(row):
        with serve_assets(assets(repo,row["commit"],site)) as url:
            summary=verify(contracts,url)["summary"]
        if summary.get("inconclusive") or not summary:return "inconclusive"
        if summary.get("changed"):return "bad"
        return "good" if set(summary)=={"matched"} else "inconclusive"
    result=locate([{"commit":sha} for sha in ordered],probe,exhaustive)
    result["schema"]="ghostdiff.git-bisect/v1"
    result["revision_count"]=len(ordered)
    result["contract_count"]=len(contracts["contracts"])
    result["limits"]="Exact local first-parent commit blobs served as static assets; no checkout or build scripts. Binary search assumes monotonic behavior. Contract scope is bounded; not causal proof. Trusted disposable repository and OS/network isolation required."
    return result
