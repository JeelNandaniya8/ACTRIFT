"""Print fixed scanner metadata for maintainer triage; no source snippets."""
from collections import Counter
import json
from pathlib import Path
import sys

p=Path("source-audit.json")
if not p.is_file():
    print("Bandit report unavailable")
    sys.exit(2)
data=json.loads(p.read_text(encoding="utf-8"))
if not isinstance(data.get("results"),list) or data.get("errors"):
    print("Bandit report incomplete")
    sys.exit(2)
counts=Counter((r["issue_severity"],r["issue_confidence"],r["test_id"]) for r in data["results"])
print("## Static security scan — review required")
print(f"Total findings: {len(data['results'])}")
for (severity,confidence,test_id),count in sorted(counts.items()):
    if severity not in ("LOW","MEDIUM","HIGH","UNDEFINED") or confidence not in ("LOW","MEDIUM","HIGH","UNDEFINED") or not test_id.startswith("B") or not test_id[1:].isdigit():
        raise ValueError("Unexpected scanner metadata")
    print(f"- {severity} / {confidence} / {test_id}: {count}")
print("This scanner report is not independent security certification.")
