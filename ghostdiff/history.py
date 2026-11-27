"""Build an offline timeline of scoped fingerprints; never modify original reports."""
import re
from .intelligence import fingerprint

def timeline(entries):
    if not isinstance(entries,list) or not 2<=len(entries)<=64:
        raise ValueError("Provide 2–64 ordered evidence captures")
    seen=set();rows=[];previous=None
    for label,evidence,side in entries:
        if not isinstance(label,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",label) or label in seen:
            raise ValueError("Invalid or duplicate revision label")
        seen.add(label)
        current=fingerprint(evidence,side)
        status="initial" if previous is None else "different_scope" if current["scope_sha256"]!=previous["scope_sha256"] else "same_observed_digest" if current["behavior_sha256"]==previous["behavior_sha256"] else "changed_observed_digest"
        rows.append({"revision":label,"status":status,**current})
        previous=current
    return {"schema":"ghostdiff.timeline/v1","revisions":rows,"limits":"Operator-supplied order and labels. Stable scoped digest comparisons only; differences are not causal proof, and agreement is not complete equivalence."}
