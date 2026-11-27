"""Append-only local SQLite history of scoped fingerprints, not raw evidence."""
import re
import sqlite3
from datetime import datetime,timezone
from contextlib import closing
from pathlib import Path
from .intelligence import fingerprint

DDL="""CREATE TABLE IF NOT EXISTS captures (
 id INTEGER PRIMARY KEY, project TEXT NOT NULL, revision TEXT NOT NULL,
 captured_at TEXT NOT NULL, scope TEXT NOT NULL, behavior TEXT NOT NULL,
 observed INTEGER NOT NULL, excluded INTEGER NOT NULL,
 UNIQUE(project, revision)
)"""
def label(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",value):raise ValueError("Invalid project or revision label")
    return value

def record(db,project,revision,evidence,side="before"):
    label(project);label(revision)
    result=fingerprint(evidence,side)
    with closing(sqlite3.connect(db,timeout=5)) as con,con:
        con.execute(DDL)
        try:
            con.execute("INSERT INTO captures(project,revision,captured_at,scope,behavior,observed,excluded) VALUES (?,?,?,?,?,?,?)",
                        (project,revision,datetime.now(timezone.utc).isoformat(),result["scope_sha256"],result["behavior_sha256"],result["observed_paths"],len(result["excluded_paths"])))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Revision already recorded; history is append-only") from exc
    return {"schema":"ghostdiff.history-record/v1","project":project,"revision":revision,"observed_paths":result["observed_paths"],"excluded_count":len(result["excluded_paths"])}

def history(db,project,limit=100):
    label(project)
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError("Limit must be 1–1000")
    if not Path(db).is_file():raise ValueError("History database not found")
    uri=Path(db).resolve().as_uri()+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True,timeout=5)) as con:
        rows=con.execute("SELECT revision,captured_at,scope,behavior,observed,excluded FROM captures WHERE project=? ORDER BY id DESC LIMIT ?",(project,limit)).fetchall()
    output=[];previous=None
    for revision,at,scope,behavior,observed,excluded in reversed(rows):
        status="initial_in_window" if previous is None else "different_scope" if scope!=previous[0] else "same_observed_digest" if behavior==previous[1] else "changed_observed_digest"
        output.append({"revision":revision,"captured_at":at,"scope_sha256":scope,"behavior_sha256":behavior,"observed_paths":observed,"excluded_count":excluded,"status":status})
        previous=(scope,behavior)
    return {"schema":"ghostdiff.history/v1","project":project,"captures":output,"limits":"Local append order, operator labels, scoped digests only. Not provenance or complete equivalence."}
