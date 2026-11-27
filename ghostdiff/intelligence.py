"""Offline, evidence-bound behavior fingerprints and reviewed rename hypotheses."""
from hashlib import sha256
from .engine import Settings,signature,stable_json,has_signal
from .matching import score,normalized

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
    scope={"observation_revision":3,"policy":policy,"paths":[r["path"] for r in stable],"authenticated":bool(evidence.get("authenticated_baseline" if side=="before" else "authenticated_candidate")),"backend_reset":bool(evidence.get("backend_reset"))}
    return {"schema":"ghostdiff.fingerprint/v1","scope_sha256":digest(scope),"behavior_sha256":digest(stable),"observed_paths":len(stable),"excluded_paths":excluded,"coverage":evidence.get("coverage",{}),"limits":"Digest of stable observed deltas only; compare only matching scope hashes and review exclusions. Not an identity, signature, or correctness proof."}

def behavior_similarity(a,b):
    """Exact deltas are strong; partial matches require a shared non-text channel."""
    if a==b:return "exact",1.0,["exact observed outcome"]
    strong=[k for k in ("route_change","downloads","actions_added","actions_removed") if a.get(k) and a.get(k)==b.get(k)]
    # Contradictory route/download behavior must not become a proposed match.
    if any(a.get(k)!=b.get(k) for k in ("route_change","downloads")):return None
    if not strong:return None
    def words(o,key):
        return set(normalized(" ".join(o.get(key,[]))))
    scores=[]
    for key in ("text_added","text_removed"):
        x,y=words(a,key),words(b,key)
        if x or y:scores.append(len(x&y)/len(x|y))
    similarity=sum(scores)/len(scores) if scores else 1.0
    if similarity<.5:return None
    return "partial",round(.6+.4*similarity,3),["shared "+k for k in strong]+["normalized text overlap"]

def match_renames(forward,reverse):
    """Review-only matching in stable shared journey contexts."""
    if forward.get("before_url")!=reverse.get("after_url") or forward.get("after_url")!=reverse.get("before_url"):
        raise ValueError("Reverse evidence must swap the exact target URLs")
    a=Settings(**forward["settings"]);b=Settings(**reverse["settings"])
    if a!=b or a.allow_writes or a.allow_risky_actions or bool(forward.get("backend_reset"))!=bool(reverse.get("backend_reset")):
        raise ValueError("Require matching read-policy settings for both captures")
    if any(report.get(k) for report in (forward,reverse) for k in ("authenticated_baseline","authenticated_candidate")):
        raise ValueError("Rename research currently requires unauthenticated fixtures")
    baseline,_=observations(forward,"before");candidate,_=observations(reverse,"before")
    def key(path):return tuple((a["role"],a["name"]) for a in path)
    def contexts(report):
        out={}
        for r in report["paths"]:
            runs=r["before"]
            if len(runs)<2 or any(x["status"]!="ok" for x in runs) or len({signature(x) for x in runs})!=1:continue
            if any(s["outcome"].get("page_errors") or s["outcome"].get("http_errors") for s in runs[0]["steps"]):continue
            final=runs[0]["final"]
            out[key(r["path"])]=(final["route"],{(x["role"],x["name"]) for x in final["actions"]})
        if () not in out:raise ValueError("Require stable initial inventory in both captures")
        return out
    ca,cb=contexts(forward),contexts(reverse)
    old={key(r["path"]):r for r in baseline}
    new={key(r["path"]):r for r in candidate}
    pairs=[]
    for path in sorted(old):
        prefix=path[:-1];action=path[-1]
        if action[0] not in ("button","link") or prefix not in ca or prefix not in cb:continue
        ra,ia=ca[prefix];rb,ib=cb[prefix]
        if ra!=rb or action not in ia-ib:continue
        x=old[path]
        hits=[]
        for other in sorted(ib-ia):
            if action[0]!=other[0] or prefix+(other,) not in new:continue
            y=new[prefix+(other,)]
            if not has_signal(x["outcomes"][-1]) or not has_signal(y["outcomes"][-1]):continue
            match=behavior_similarity(x["outcomes"][-1],y["outcomes"][-1])
            if match:
                strength,similarity,reasons=match
                hits.append({"role":other[0],"name":other[1],"label_score":score(action[1],other[1]),"behavior_score":similarity,"strength":strength,"reasons":reasons})
        pairs.append({"from":{"role":action[0],"name":action[1]},"path":x["path"],"step":len(path)-1,"contract_id":digest(x["path"])[:16],"candidates":sorted(hits,key=lambda h:(h["strength"]!="exact",-h["behavior_score"],-h["label_score"],h["name"]))})
    counts={}
    for pair in pairs:
        for h in pair["candidates"]:
            k=(key(pair["path"][:-1]),h["role"],h["name"]);counts[k]=counts.get(k,0)+1
    for pair in pairs:
        hits=pair["candidates"]
        unique=len(hits)==1 and counts[(key(pair["path"][:-1]),hits[0]["role"],hits[0]["name"])]==1
        pair["status"]=("review_required" if hits[0]["strength"]=="exact" else "possible_match") if unique else "ambiguous" if hits else "no_observed_match"
    return {"schema":"ghostdiff.rename-hypotheses/v1","hypotheses":pairs,"limits":"Stable shared-prefix context and final-step observable deltas; partial candidates require shared non-text evidence. Not semantic equivalence. Unobserved or unstable actions can be excluded; no alias is approved or executed."}
