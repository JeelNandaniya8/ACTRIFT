"""Scope synthetic test storage to the target host and origin."""
import json
from pathlib import Path
from urllib.parse import urlsplit

def local_storage_state(source,url):
    if source is None:
        return None
    if isinstance(source,(str,Path)):
        p=Path(source)
        if p.stat().st_size>2*1024*1024:
            raise ValueError("Storage state exceeds 2 MiB")
        data=json.loads(p.read_text(encoding="utf-8"))
    else:
        data=source
    if not isinstance(data,dict) or set(data)-{"cookies","origins"}:
        raise ValueError("Invalid test storage state")
    cookies,origins=data.get("cookies",[]),data.get("origins",[])
    if not isinstance(cookies,list) or not isinstance(origins,list) or len(cookies)>200 or len(origins)>10:
        raise ValueError("Invalid test storage state entries")
    target=urlsplit(url)
    def key(u):
        x=urlsplit(u)
        return (x.scheme,x.hostname,x.port if x.port is not None else (443 if x.scheme=="https" else 80))
    for cookie in cookies:
        if not isinstance(cookie,dict) or cookie.get("domain") not in (target.hostname,"."+target.hostname):
            raise ValueError("Cookie domain must match the local test host")
        if "partitionKey" in cookie:
            raise ValueError("Partitioned test cookies are not supported")
    for entry in origins:
        if not isinstance(entry,dict) or not isinstance(entry.get("origin"),str) or key(entry["origin"])!=key(url):
            raise ValueError("Storage origin must match the exact local test origin")
    return {"cookies":cookies,"origins":origins}
