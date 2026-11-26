"""Portable interactive behavior-tree report. All observations are escaped."""
import html
import json


def render_observatory(report):
    e=lambda value:html.escape(str(value),quote=True)
    nodes={}
    for idx,row in enumerate(report["paths"]):
        key=tuple((a["role"],a["name"]) for a in row["path"])
        nodes[key]=(idx,row)
    children={}
    for key in nodes:
        if key:
            children.setdefault(key[:-1],[]).append(key)
    def render(key):
        idx,row=nodes[key]
        status=row["status"]
        title=key[-1][1] if key else "Initial inventory"
        evidence=e(json.dumps({"before":row["before"],"after":row["after"]},indent=2,ensure_ascii=False))
        desc=e(row["reason"])
        sub="".join(render(k) for k in children.get(key,[]))
        return f'<li data-status="{e(status)}"><details {"open" if not key else ""}><summary><span class="node">{e(title)}</span><span class="state">{e(status.replace("_"," "))}</span></summary><p>{desc}</p><details><summary>Repeated evidence · {idx:02d}</summary><pre>{evidence}</pre></details></details>{("<ul>"+sub+"</ul>") if sub else ""}</li>'
    tree=render(()) if () in nodes else ""
    stats="".join(f'<div><b>{e(v)}</b><span>{e(k.replace("_"," "))}</span></div>' for k,v in sorted(report["summary"].items()))
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GHOSTDIFF Observatory</title><style>
:root{color-scheme:light dark;--bg:#f5f6f8;--ink:#202635;--line:#aab5c4;--muted:#526074;--accent:#126b56;--danger:#ad3c29} @media(prefers-color-scheme:dark){:root{--bg:#171c25;--ink:#eef1f6;--line:#485465;--muted:#b0bac8;--accent:#75d5ba;--danger:#ffab98}}*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font:15px/1.55 system-ui;margin:0}main{max-width:1100px;padding:42px 24px;margin:auto}h1{font-size:clamp(34px,6vw,64px);letter-spacing:-.055em;margin:12px 0}header{border-bottom:1px solid var(--line);padding-bottom:24px}.eyebrow{font:12px monospace;letter-spacing:.16em;color:var(--muted)}.stats{display:flex;flex-wrap:wrap;gap:24px;padding:24px 0}.stats div{min-width:120px;flex:1;border-top:2px solid var(--line);padding-top:12px}.stats b{display:block;font-size:30px}.stats span{color:var(--muted);font-size:12px}ul{list-style:none;padding-left:20px}li{border-left:1px solid var(--line);padding-left:16px;margin:10px 0}summary{cursor:pointer;display:flex;gap:12px;flex-wrap:wrap;justify-content:space-between;border-bottom:1px solid var(--line);padding:9px 0}.state{font-size:12px;color:var(--muted)}[data-status=equivalent_observed]>details>summary>.state{color:var(--accent)}[data-status=unmatched]>details>summary>.state,[data-status=behavior_changed]>details>summary>.state,[data-status=download_changed]>details>summary>.state{color:var(--danger)}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto;padding:12px;border:1px solid var(--line)}button{padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:transparent;color:inherit;cursor:pointer}button:focus-visible,summary:focus-visible{outline:2px solid var(--accent)}footer{color:var(--muted);margin-top:36px;font-size:13px}</style><body><main><header><div class="eyebrow">GHOSTDIFF / OBSERVATORY</div><h1>Behavioral DNA</h1><p>Explore observed journeys, not inferred features. Select a node to inspect its evidence.</p></header><div class="stats">"""+stats+"""</div><button type="button" id="expand">Expand journeys</button> <button type="button" id="collapse">Collapse journeys</button><ul>"""+tree+"""</ul><footer>"""+e(report["limits"])+"""</footer></main><script>const toggle=open=>document.querySelectorAll('li>details').forEach(x=>x.open=open);document.getElementById('expand').onclick=()=>toggle(true);document.getElementById('collapse').onclick=()=>toggle(false);</script></body></html>"""
