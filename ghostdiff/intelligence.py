"""Offline, evidence-bound behavior fingerprints and reviewed rename hypotheses."""
from hashlib import sha256
from .engine import Settings,signature,stable_json,has_signal
from .matching import score

def digest(value):
    return sha256(stable_json(value).encode("utf-8")).hexdigest()

def observations(evidence,side):
    if evidence.get("schema")!="ghostdiff.evidence/v1" or evidence.get("observation_revision")!=3:
        raise ValueError("Require revision-3 discovery evidence")
    if side not in ("before","after"):
        raise ValueError("Invalid evidence side")
    cfg=Settings(**evidence["settings"]);cfg.validate()
    paths=evidence["paths"]
    if not isinstance(paths,list) or len(paths)>200:
        raise ValueError("Invalid evidence path count")
    stable=[];excluded=[];seen=set()
    for row in paths:
        path=row["path"]
        key=stable_json(path)
        if key in seen: raise ValueError("Duplicate evidence path")
        seen.add(key)
        if not path: continue
        runs=row[side]
        if len(runs)<2 or len(runs)>5 or any(r["status"]!="ok" for r in runs) or len({signature(r) for r in runs})!=1:
            excluded.append({"path":path,"reason":"unstable or unsuccessful"});continue
        steps=runs[0]["steps"]
        if len(steps)!=len(path) or any(s.get("action")!=a for s,a in zip(steps,path)):
            excluded.append({"path":path,"reason":"step mismatch"});continue
        outcomes=[s["outcome"] for s in steps]
        if any(o.get("page_errors") or o.get("http_errors") for o in outcomes) or not any(has_signal(o) for o in outcomes):
            excluded.append({"path":path,"reason":"unhealthy or unobserved"});continue
        stable.append({"path":path,"outcomes":outcomes})
    return sorted(stable,key=lambda x:stable_json(x["path"])),excluded

def fingerprint(evidence,side="before"):
    stable,excluded=observations(evidence,side)
    if not stable: raise ValueError("No stable observable paths to fingerprint")
    cfg=Settings(**evidence["settings"])
    policy={k:getattr(cfg,k) for k in ("browser","depth","budget","repeats","settle_ms","timeout_ms","ignore","mask_text","allow_writes","allow_risky_actions")}
    scope={"observation_revision":3,"policy":policy,"paths":[r["path"] for r in stable],"authenticated":bool(evidence.get("authenticated_baseline" if side=="before" else "authenticated_candidate"))}
    return {"schema":"ghostdiff.fingerprint/v1","scope_sha256":digest(scope),"behavior_sha256":digest(stable),"observed_paths":len(stable),"excluded_paths":excluded,"coverage":evidence.get("coverage",{}),"limits":"Digest of stable observed deltas only; compare only matching scope hashes and review exclusions. Not an identity, signature, or correctness proof."}

def match_renames(forward,reverse):
    """Compare independently observed one-step actions; never click or approve."""
    if forward.get("before_url")!=reverse.get("after_url") or forward.get("after_url")!=reverse.get("before_url"):
        raise ValueError("Reverse evidence must swap the exact target URLs")
    a=Settings(**forward["settings"]);b=Settings(**reverse["settings"])
    if a!=b or a.allow_writes or a.allow_risky_actions:
        raise ValueError("Require matching read-policy settings for both captures")
    if forward.get("authenticated_baseline") or forward.get("authenticated_candidate") or reverse.get("authenticated_baseline") or reverse.get("authenticated_candidate"):
        raise ValueError("Rename research currently requires unauthenticated fixtures")
    baseline,_=observations(forward,"before");candidate,_=observations(reverse,"before")
    def first(rows):
        return {(r["path"][0]["role"],r["path"][0]["name"]):r for r in rows if len(r["path"])==1 and r["path"][0]["role"] in ("button","link")}
    old,new=first(baseline),first(candidate)
    pairs=[]
    for key in sorted(old.keys()-new.keys()):
        x=old[key]
        hits=[]
        for other in sorted(new.keys()-old.keys()):
            if key[0]==other[0] and x["outcomes"]==new[other]["outcomes"]:
                hits.append({"role":other[0],"name":other[1],"label_score":score(key[1],other[1])})
        pairs.append({"from":{"role":key[0],"name":key[1]},"contract_id":digest(x["path"])[:16],"candidates":sorted(hits,key=lambda h:(-h["label_score"],h["name"]))})
    counts={}
    for pair in pairs:
        for h in pair["candidates"]:
            key=(h["role"],h["name"]);counts[key]=counts.get(key,0)+1
    for pair in pairs:
        hits=pair["candidates"]
        pair["status"]="review_required" if len(hits)==1 and counts[(hits[0]["role"],hits[0]["name"])]==1 else "ambiguous" if hits else "no_observed_match"
    return {"schema":"ghostdiff.rename-hypotheses/v1","hypotheses":pairs,"limits":"One-step exact observable delta matches only; label scores are heuristics. Missing, unobserved or unstable actions may be excluded. No alias is approved or executed."}
