"""Explicit, non-executable JSON configuration for read-policy comparisons."""
from .engine import Settings,validate_url
ALLOWED={"depth","budget","settle_ms","timeout_ms","repeats","browser","ignore","mask_text","screenshots","parallel","api_paths"}
def parse_config(data):
    if not isinstance(data,dict) or set(data)!={"schema","before","after","settings","bidirectional","strict"} or data["schema"]!="ghostdiff.config/v1":
        raise ValueError("Unsupported comparison configuration")
    raw=data["settings"]
    if not isinstance(raw,dict) or set(raw)-ALLOWED:
        raise ValueError("Unsupported or unsafe config setting")
    if type(data["bidirectional"]) is not bool or type(data["strict"]) is not bool:
        raise ValueError("Config policy flags must be boolean")
    validate_url(data["before"]);validate_url(data["after"])
    cfg=Settings(**raw);cfg.validate()
    return data["before"],data["after"],cfg,data["bidirectional"],data["strict"]
