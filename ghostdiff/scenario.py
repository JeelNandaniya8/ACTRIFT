"""Explicit synthetic form journeys; never guess input or submit unknown forms."""
from collections import Counter
from dataclasses import asdict,replace
from playwright.sync_api import sync_playwright
from .engine import Action,Settings,compare_path,experiment,launch_browser,validate_url,validate_path

def parse_spec(spec):
    if not isinstance(spec,dict) or set(spec)!={"schema","journeys"} or spec["schema"]!="ghostdiff.journeys/v1":
        raise ValueError("Unsupported journey specification")
    items=spec["journeys"]
    if not isinstance(items,list) or not 1<=len(items)<=20:
        raise ValueError("Provide 1–20 explicit journeys")
    names=set()
    parsed=[]
    for item in items:
        if not isinstance(item,dict) or set(item)!={"name","steps"}:
            raise ValueError("Invalid journey fields")
        name=item["name"]
        steps=item["steps"]
        if not isinstance(name,str) or not 1<=len(name)<=100 or name in names or not isinstance(steps,list) or not 1<=len(steps)<=5:
            raise ValueError("Invalid or duplicate journey name or step count")
        names.add(name)
        path=[]; values={}
        for i,step in enumerate(steps):
            if not isinstance(step,dict):
                raise ValueError("Invalid journey step")
            kind=step.get("action")
            if kind=="fill" and set(step) in ({"action","name","value"},{"action","name","value","role"}):
                path.append(Action(step.get("role","textbox"),step["name"]))
                values[i]=step["value"]
            elif kind in ("check","uncheck") and set(step)=={"action","name"}:
                path.append(Action("checkbox",step["name"]))
                values[i]={"op":kind}
            elif kind=="select" and set(step)=={"action","name","label"}:
                path.append(Action("combobox",step["name"]))
                values[i]={"op":"select","label":step["label"]}
            elif kind=="press" and set(step) in ({"action","name","key"},{"action","name","key","role"}):
                path.append(Action(step.get("role","textbox"),step["name"]))
                values[i]={"op":"press","key":step["key"]}
            elif kind=="click" and set(step)=={"action","role","name"} and step["role"] in ("button","link"):
                path.append(Action(step["role"],step["name"]))
            elif kind=="reload" and set(step)=={"action"}:
                path.append(Action("reload","Reload page"))
            else:
                raise ValueError("Unsupported explicit step")
        validate_path(path,Settings(depth=5),values)
        parsed.append((name,tuple(path),values))
    return parsed

def run_journeys(spec,before,after,cfg=None,before_state=None,after_state=None):
    cfg=replace(cfg or Settings(),depth=5,allow_writes=False,allow_risky_actions=False)
    cfg.validate();validate_url(before);validate_url(after)
    journeys=parse_spec(spec)
    rows=[]
    with sync_playwright() as p:
        browser=launch_browser(p,cfg)
        try:
            for name,path,values in journeys:
                runs_a=[experiment(browser,before,path,replace(cfg,screenshots=cfg.screenshots and i==0),before_state,values) for i in range(cfg.repeats)]
                runs_b=[experiment(browser,after,path,replace(cfg,screenshots=cfg.screenshots and i==0),after_state,values) for i in range(cfg.repeats)]
                status,reason=compare_path(runs_a,runs_b)
                rows.append({"name":name,"path":[asdict(x) for x in path],"status":status,"reason":reason,"before":runs_a,"after":runs_b})
        finally:
            browser.close()
    return {"schema":"ghostdiff.journey-evidence/v1","before_url":before,"after_url":after,"settings":asdict(cfg),
            "summary":dict(Counter(x["status"] for x in rows)),"paths":rows,
            "limits":"Explicit synthetic form journeys only. Rendered input values may appear in evidence. Replay with the original journey specification; this evidence cannot be frozen as discovery contracts."}
