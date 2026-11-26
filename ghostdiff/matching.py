"""Conservative, local action-name matching suggestions. Never auto-click."""
from difflib import SequenceMatcher
import re
import unicodedata

SYNONYMS = {
    "download":"export", "export":"export", "save":"save", "store":"save",
    "remove":"delete", "delete":"delete", "preferences":"settings",
    "settings":"settings", "signout":"logout", "logout":"logout",
    "signin":"login", "login":"login", "find":"search", "search":"search",
    "dismiss":"close", "close":"close",
}
STOP={"the","a","an","to","my","your"}

def normalized(name):
    name=unicodedata.normalize("NFKC",name).casefold()
    name=re.sub(r"\bsign[\s-]+(in|out)\b",r"sign\1",name)
    words=re.findall(r"[^\W_]+",name)
    return tuple(SYNONYMS.get(word,word) for word in words if word not in STOP)

def score(a,b):
    x,y=normalized(a),normalized(b)
    if not x or not y:
        return 0.0
    if x==y:
        return 1.0
    overlap=len(set(x)&set(y))/len(set(x)|set(y))
    sequence=SequenceMatcher(None," ".join(x)," ".join(y),autojunk=False).ratio()
    return round(.65*overlap+.35*sequence,3)

def suggestions(role,name,actions,limit=5):
    candidates=[]
    for action in actions:
        if action.role!=role or action.name==name:
            continue
        similarity=score(name,action.name)
        if similarity>=.45:
            candidates.append({"role":role,"name":action.name,"score":similarity})
    candidates.sort(key=lambda c:(-c["score"],c["name"]))
    return candidates[:limit]
