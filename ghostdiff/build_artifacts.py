"""Serve operator-provided, checksum-bound prebuilt static frontend artifacts.

No source build, archive extraction, arbitrary command, or remote download.
Commit labels are operator assertions; the digest binds bytes, not provenance.
"""
import hashlib
import json
import re
from pathlib import Path
from .bisect import locate
from .contracts import freeze,verify
from .engine import Settings,compare
from .gitintel import serve_assets
from .static_bundle import pack_site,decode_site,_unique_pairs

SCHEMA="ghostdiff.build-artifact/v1"
MAX_ARTIFACT=24*1024*1024
MAX_MANIFEST=65536
SHA=re.compile(r"[0-9a-f]{40}")
DIGEST=re.compile(r"[0-9a-f]{64}")
FILE=re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,190}\.json")

def read_bounded(path,limit):
    if not path.is_file():raise ValueError("Expected a regular local file")
    with path.open("rb") as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError("Artifact or manifest exceeds limit")
    return raw

def pack_artifact(directory,commit,out):
    if not isinstance(commit,str) or not SHA.fullmatch(commit):
        raise ValueError("Require a full lowercase commit SHA")
    path=Path(out)
    if not FILE.fullmatch(path.name):raise ValueError("Use a simple .json artifact filename")
    raw=json.dumps({"schema":SCHEMA,"commit":commit,"assets":pack_site(directory)},sort_keys=True,separators=(",",":")).encode("utf-8")
    if len(raw)>MAX_ARTIFACT:raise ValueError("Artifact exceeds size limit")
    with path.open("xb") as stream:
        stream.write(raw)
    return {"commit":commit,"artifact":path.name,"sha256":hashlib.sha256(raw).hexdigest()}

def parse_manifest(path):
    path=Path(path).resolve(strict=True)
    data=json.loads(read_bounded(path,MAX_MANIFEST).decode("utf-8"),object_pairs_hook=_unique_pairs)
    if not isinstance(data,dict) or set(data)!={"schema","revisions"} or data["schema"]!="ghostdiff.build-revisions/v1":
        raise ValueError("Unsupported build artifact manifest")
    rows=data["revisions"]
    if not isinstance(rows,list) or not 2<=len(rows)<=64:raise ValueError("Provide 2–64 ordered build artifacts")
    commits=set();names=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"commit","artifact","sha256"}:
            raise ValueError("Invalid build revision entry")
        for key,pattern in (("commit",SHA),("artifact",FILE),("sha256",DIGEST)):
            if not isinstance(row[key],str) or not pattern.fullmatch(row[key]):
                raise ValueError("Invalid commit, artifact filename or SHA-256")
        if row["commit"] in commits or row["artifact"] in names:raise ValueError("Duplicate build revision")
        commits.add(row["commit"]);names.add(row["artifact"])
    return path.parent,rows

def load_artifact(root,row):
    path=root/row["artifact"]
    if path.is_symlink() or not path.is_file() or path.resolve().parent!=root:
        raise ValueError("Artifact must be a regular adjacent file")
    raw=read_bounded(path,MAX_ARTIFACT)
    if hashlib.sha256(raw).hexdigest()!=row["sha256"]:raise ValueError("Artifact checksum mismatch")
    data=json.loads(raw.decode("utf-8"),object_pairs_hook=_unique_pairs)
    if not isinstance(data,dict) or set(data)!={"schema","commit","assets"} or data["schema"]!=SCHEMA or data["commit"]!=row["commit"]:
        raise ValueError("Artifact schema or commit label mismatch")
    return decode_site(data["assets"])

def build_bisect(manifest,contracts=None,exhaustive=False,cfg=None):
    root,rows=parse_manifest(manifest)
    # All manifests are validated before any browser action; bytes are rechecked
    # when provisioned, avoiding unbounded retention of multiple builds.
    for row in rows:
        load_artifact(root,row)
    if contracts is None:
        files=load_artifact(root,rows[0])
        with serve_assets(files) as a,serve_assets(files) as b:
            contracts=freeze(compare(a,b,cfg or Settings(depth=1,budget=16)))
    if contracts.get("authenticated"):
        raise ValueError("Build artifact bisection supports unauthenticated contracts only")
    def probe(row):
        with serve_assets(load_artifact(root,row)) as url:
            summary=verify(contracts,url)["summary"]
        if not summary or summary.get("inconclusive"):return "inconclusive"
        if summary.get("changed"):return "bad"
        return "good" if set(summary)=={"matched"} else "inconclusive"
    result=locate(rows,probe,exhaustive)
    result.update(schema="ghostdiff.build-bisect/v1",revision_count=len(rows),contract_count=len(contracts["contracts"]),
                  artifacts=[{"commit":r["commit"],"sha256":r["sha256"]} for r in rows],
                  limits="Operator-ordered prebuilt static frontend artifacts. SHA-256 binds bytes, not Git/build provenance. No shell, checkout, backend or build execution. Boundaries apply to supplied observations only; binary mode assumes monotonic failures.")
    return result
