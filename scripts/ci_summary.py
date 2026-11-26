"""Write only fixed labels and numeric counts to the CI summary."""
import json
import sys
from pathlib import Path

print("## GHOSTDIFF behavior check")
p=Path(sys.argv[1])
if not p.is_file():
    print("No complete report was produced.")
else:
    data=json.loads(p.read_text(encoding="utf-8"))
    summary=data["summary"]
    for key in ("equivalent_observed","behavior_changed","download_changed","unmatched","unobserved","inconclusive"):
        print(f"- {key}: {int(summary.get(key,0))}")
    print(f"- Skipped action entries: {len(data.get('skipped_actions',[]))}")
    print("Observed changes require review; untested behavior is not certified.")
