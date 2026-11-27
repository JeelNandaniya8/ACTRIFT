"""Build synthetic fixtures for the actual network-disabled Docker CI smoke."""
import base64
import json
from pathlib import Path

def site(text):
    source=f"<!doctype html><button onclick=\"document.querySelector('p').textContent='{text}'\">Export</button><p>Ready</p>"
    return {"index.html":base64.b64encode(source.encode()).decode("ascii")}

if __name__=="__main__":
    for name,value in (("clean","Done"),("broken","Broken")):
        Path(name+"-static.json").write_text(json.dumps({"schema":"ghostdiff.static-bundle/v1","before":site("Done"),"after":site(value)}),encoding="utf-8")
