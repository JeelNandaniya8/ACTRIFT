"""Locate a regression boundary among explicitly provisioned local revisions."""
import re
from .engine import validate_url
from .contracts import verify

def parse_manifest(data):
    if not isinstance(data,dict) or set(data)!={"schema","revisions"} or data["schema"]!="ghostdiff.revisions/v1":
        raise ValueError("Unsupported revision manifest")
    rows=data["revisions"]
    if not isinstance(rows,list) or not 2<=len(rows)<=64:
        raise ValueError("Provide 2–64 ordered revisions")
    seen=set();urls=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"commit","url"} or not isinstance(row["commit"],str) or not re.fullmatch("[0-9a-f]{40}",row["commit"]):
            raise ValueError("Require a full lowercase commit SHA and local URL")
        validate_url(row["url"])
        if row["commit"] in seen or row["url"] in urls:raise ValueError("Duplicate revision or URL")
        seen.add(row["commit"]);urls.add(row["url"])
    return rows

def locate(rows,probe,exhaustive=False):
    """Binary search assumes monotonic regression; exhaustive mode checks it."""
    tested={}
    def check(i):
        if i not in tested:
            status=probe(rows[i])
            if status not in ("good","bad","inconclusive"):raise ValueError("Invalid probe verdict")
            tested[i]=status
        return tested[i]
    lo,hi=0,len(rows)-1
    if check(lo)!="good" or check(hi)!="bad":
        status="invalid_endpoints"
    else:
        status="suspected_boundary"
        while hi-lo>1:
            mid=(lo+hi)//2;result=check(mid)
            if result=="inconclusive":
                status="inconclusive";break
            if result=="good":lo=mid
            else:hi=mid
        if exhaustive:
            for i in range(len(rows)):check(i)
            observed=[tested[i] for i in range(len(rows))]
            if "inconclusive" in observed:status="inconclusive"
            elif observed==sorted(observed,key=lambda x:x=="bad"):
                hi=observed.index("bad");lo=hi-1;status="observed_boundary"
            else:status="non_monotonic"
    boundary={"last_good":rows[lo]["commit"],"first_bad":rows[hi]["commit"]} if status in ("suspected_boundary","observed_boundary") else None
    return {"schema":"ghostdiff.bisect/v1","status":status,"boundary":boundary,"tested":[{"commit":rows[i]["commit"],"status":v} for i,v in sorted(tested.items())],"limits":"Revision order and deployment identity are supplied by the operator. No checkout, build or shell execution; binary mode assumes monotonic failures. Boundary is relative to the supplied list and contracts, not proof of causal change."}

def bisect(manifest,contracts,exhaustive=False):
    rows=parse_manifest(manifest)
    if contracts.get("authenticated"):raise ValueError("Bisect currently supports unauthenticated contracts only")
    def probe(row):
        summary=verify(contracts,row["url"])["summary"]
        if summary.get("inconclusive") or not summary:return "inconclusive"
        if summary.get("changed"):return "bad"
        return "good" if set(summary)=={"matched"} else "inconclusive"
    return locate(rows,probe,exhaustive)
