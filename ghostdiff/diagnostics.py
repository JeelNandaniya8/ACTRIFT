"""Explain the first observed divergence without claiming source causation."""
from .engine import stable_json,signature

def diagnose(report):
    if report.get("schema") not in ("ghostdiff.evidence/v1","ghostdiff.journey-evidence/v1"):
        raise ValueError("Unsupported evidence schema")
    findings=[]
    for row in report["paths"]:
        if row["status"] not in ("unmatched","behavior_changed","download_changed","inconclusive"):continue
        before,after=row["before"],row["after"]
        stable=all(len(r)>=2 and len({signature(x) for x in r})==1 for r in (before,after))
        a=before[0] if before else {};b=after[0] if after else {}
        first=None
        if stable:
            for i,(x,y) in enumerate(zip(a.get("steps",[]),b.get("steps",[]))):
                old,new=x["outcome"],y["outcome"]
                if old!=new:
                    keys=sorted(k for k in old.keys()|new.keys() if stable_json(old.get(k))!=stable_json(new.get(k)))
                    first={"step":i+1,"action":row["path"][i],"changed_fields":keys,"http_errors":new.get("http_errors",[]),"javascript_errors":new.get("page_errors",[]),"baseline_downloads":old.get("downloads",[]),"candidate_downloads":new.get("downloads",[])}
                    break
            if first is None and b.get("status")=="unmatched":
                i=b.get("at")
                if type(i) is int and 0<=i<len(row["path"]):
                    first={"step":i+1,"action":row["path"][i],"changed_fields":["accessible_action_missing"]}
        findings.append({"path":row["path"],"status":row["status"],"repeated_observations_stable":stable,"first_observed_divergence":first,"reason":row["reason"]})
    return {"schema":"ghostdiff.diagnostics/v1","findings":findings,"limits":"Evidence-localization only. HTTP paths, exception messages and changed fields are diagnostic leads, not source-file or causal attribution."}
