"""Machine-readable, data-minimized evidence summaries for local automation."""
from collections import Counter
from .gate import exit_code

STATUSES=("inventory","equivalent_observed","behavior_changed","download_changed","unmatched","unobserved","inconclusive")
COVERAGE=("executed_paths","path_budget","depth_limit","omitted_budget_branches","depth_frontiers","skipped_action_entries")

def summarize(report,strict=False):
    if type(strict) is not bool:raise ValueError("Strict policy must be boolean")
    if not isinstance(report,dict) or report.get("schema")!="ghostdiff.evidence/v1" or report.get("observation_revision")!=3:
        raise ValueError("Unsupported evidence schema")
    rows=report["paths"]
    if not isinstance(rows,list) or not 1<=len(rows)<=200:
        raise ValueError("Invalid evidence path count")
    counts=Counter()
    findings=[]
    for index,row in enumerate(rows):
        status=row["status"];path=row["path"]
        if status not in STATUSES or not isinstance(path,list) or len(path)>5:
            raise ValueError("Invalid evidence row")
        counts[status]+=1
        if status in ("behavior_changed","download_changed","unmatched","inconclusive","unobserved"):
            findings.append({"evidence_index":index,"status":status,"depth":len(path)})
    if dict(counts)!=report["summary"]:
        raise ValueError("Evidence summary does not match rows")
    for name in ("baseline_only_actions","candidate_only_actions","skipped_actions"):
        if not isinstance(report.get(name,[]),list):raise ValueError("Invalid evidence inventory")
    source=report.get("coverage",{})
    coverage={}
    for key in COVERAGE:
        if key in source:
            value=source[key]
            if type(value) is not int or value<0:raise ValueError("Invalid coverage counter")
            coverage[key]=value
    if coverage.get("executed_paths",len(rows))!=len(rows):
        raise ValueError("Coverage does not match path count")
    code=exit_code(report,strict=strict)
    return {"schema":"ghostdiff.agent-result/v1","execution_status":"completed",
            "verdict":("matched_observations" if code==0 else "differences_observed" if code==1 else "inconclusive"),
            "exit_code":code,"strict":strict,"summary":{key:counts[key] for key in STATUSES},
            "coverage":coverage,"baseline_only_count":len(report.get("baseline_only_actions",[])),
            "candidate_only_count":len(report.get("candidate_only_actions",[])),
            "skipped_count":len(report.get("skipped_actions",[])),"findings":findings,
            "limits":"Observed bounded scope only. No raw page text, URLs, action labels, screenshots, hashes or exception messages included. Evidence is not authenticated or proof of correctness."}
