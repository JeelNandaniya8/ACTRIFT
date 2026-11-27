"""Rank changed source hunks against observed diagnostic leads, not causal proof."""
import re
from .gitintel import git,commit
from .diagnostics import diagnose
from .sourcemap import map_locations

EXTENSIONS=(".js",".jsx",".ts",".tsx",".html",".htm",".py",".css",".vue",".svelte",".go",".java",".rs",".rb",".php",".cs")
HUNK=re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@(.*)$")
def changed_hunks(repo,good,bad):
    commit(repo,good);commit(repo,bad)
    names=git(repo,"diff","--no-ext-diff","--no-textconv","--name-only","-z",good,bad,"--").decode("utf-8").split("\0")
    names=[n for n in names if n.endswith(EXTENSIONS)]
    if len(names)>100:raise ValueError("Source comparison exceeds 100 changed source files")
    result=[]
    for name in names:
        raw=git(repo,"diff","--no-ext-diff","--no-textconv","--unified=0",good,bad,"--",":(literal)"+name,limit=512*1024).decode("utf-8",errors="replace")
        current=None
        for line in raw.splitlines():
            match=HUNK.match(line)
            if match:
                current={"file":name,"line":int(match[1]),"line_count":int(match[2] or "1"),"context":match[3].strip()[:160],"text":[]}
                result.append(current)
                if len(result)>2000:raise ValueError("Too many changed source hunks")
            elif current is not None and line.startswith(("+","-")) and not line.startswith(("+++","---")):
                current["text"].append(line[1:])
    return result

def rank_hunks(hunks,divergence):
    action=divergence.get("action",{}).get("name","").casefold()
    paths=[e.get("path","").casefold() for e in divergence.get("http_errors",[]) if isinstance(e,dict)]
    errors=[str(e).casefold() for e in divergence.get("javascript_errors",[])]
    locations=divergence.get("source_locations",[])
    result=[]
    for h in hunks:
        text="\n".join(h["text"]).casefold()
        name=h["file"].casefold()
        reasons=[];score=0
        if len(action)>=4 and action in text:score+=3;reasons.append("literal action label in changed lines")
        for path in set(paths):
            if path and path!="/" and path in text:score+=5;reasons.append("observed HTTP path in changed lines")
        for loc in locations:
            runtime=str(loc.get("path","")).lstrip("/")
            if runtime and (h["file"]==runtime or h["file"].endswith("/"+runtime)):
                score+=6;reasons.append("runtime stack path matches source suffix")
                line=loc.get("line")
                if type(line) is int and h["line"]<=line<h["line"]+max(1,h["line_count"]):
                    score+=4;reasons.append("runtime line overlaps changed hunk")
        for err in set(errors):
            # Match explicit quoted identifiers only; generic exception text is weak.
            for token in set(re.findall(r"['\"]([a-z_$][a-z0-9_$.]{3,50})['\"]",err)):
                if token in text:score+=2;reasons.append("quoted exception identifier in changed lines")
        if score:result.append({"file":h["file"],"line":h["line"],"line_count":h["line_count"],"context":h["context"],"score":score,"reasons":sorted(set(reasons))})
    return sorted(result,key=lambda x:(-x["score"],x["file"],x["line"]))[:10]

def localize(repo,good,bad,evidence,maps=None):
    hunks=changed_hunks(repo,good,bad)
    findings=diagnose(evidence)["findings"]
    for f in findings:
        divergence=f["first_observed_divergence"] or {}
        mapped=map_locations(divergence.get("source_locations",[]),maps or {})
        f["mapped_locations"]=mapped
        f["source_candidates"]=rank_hunks(hunks,{**divergence,"source_locations":divergence.get("source_locations",[])+mapped})
    return {"schema":"ghostdiff.source-diagnostics/v1","good":good,"bad":bad,"changed_hunks":len(hunks),"findings":findings,"limits":"Heuristic association of Git diff hunks with runtime paths, labels and errors. Explicit offline source maps supply approximate segment coordinates; deployment identity and causal attribution are not established. No source lines are copied into output; hunk context may contain source identifiers."}
