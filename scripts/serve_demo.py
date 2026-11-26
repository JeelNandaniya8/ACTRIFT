"""Serve three disposable demo variants for composite-action verification."""
import json
from pathlib import Path
import sys
from threading import Event
from ghostdiff.demo import app,serve

with serve(app()) as before,serve(app(redesign=True)) as clean,serve(app(broken=True)) as broken:
    Path(sys.argv[1]).write_text(json.dumps({"before":before,"clean":clean,"broken":broken}),encoding="utf-8")
    Event().wait()
