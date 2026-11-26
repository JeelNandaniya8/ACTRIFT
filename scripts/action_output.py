"""Emit fixed labels and numeric counts, never application-controlled text."""
import json
import sys
from pathlib import Path

p=Path(sys.argv[1])
if not p.is_file():
    print("summary=No complete report")
else:
    s=json.loads(p.read_text(encoding="utf-8"))["summary"]
    keys=("equivalent_observed","behavior_changed","download_changed","unmatched","unobserved","inconclusive")
    print("summary="+", ".join(f"{k}: {int(s.get(k,0))}" for k in keys))
