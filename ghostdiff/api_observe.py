"""Explicit, bounded JSON response observation. Never store raw response bodies."""
import json
import hashlib
import re

MAX_JSON=65536

def validate_paths(paths):
    if not isinstance(paths,(tuple,list)) or len(paths)>20 or len(set(paths))!=len(paths):
        raise ValueError("Provide at most 20 distinct API paths")
    for p in paths:
        if not isinstance(p,str) or not re.fullmatch(r"/[A-Za-z0-9_./~-]{0,199}",p) or p.startswith("//") or any(part in (".","..") for part in p.split("/")):
            raise ValueError("API observation paths must be exact local paths without query strings")

def json_digest(body):
    if len(body)>MAX_JSON:raise ValueError("JSON response exceeds observation limit")
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError("Duplicate JSON key")
            result[k]=v
        return result
    def invalid(value):raise ValueError("Non-finite JSON value")
    value=json.loads(body.decode("utf-8"),object_pairs_hook=pairs,parse_constant=invalid)
    encoded=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()

def observe_response(response,path):
    """Require a bounded declared body size; missing metadata is inconclusive."""
    status=response.status
    result={"path":path,"method":response.request.method,"status":status}
    if status in (204,304):
        return result
    headers=response.headers
    kind=headers.get("content-type","").split(";")[0].strip().lower()
    if kind!="application/json" and not kind.endswith("+json"):
        raise ValueError("Selected API response is not JSON")
    length=headers.get("content-length","")
    if not length.isdecimal() or int(length)>MAX_JSON or headers.get("content-encoding","identity").lower()!="identity":
        raise ValueError("Selected API response lacks a bounded uncompressed length")
    body=response.body()
    if len(body)!=int(length):raise ValueError("Selected API response length mismatch")
    result["json_sha256"]=json_digest(body)
    return result
