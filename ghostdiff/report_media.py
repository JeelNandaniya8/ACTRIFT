"""Optional screenshot presentation. Images are evidence, never a pass criterion."""
import base64
import binascii

def screenshots(row):
    figures=[]
    for key,title in (("before","Before"),("after","After")):
        runs=row.get(key,[])
        data=runs[0].get("screenshot_jpeg") if runs else None
        if not isinstance(data,str) or len(data)>700000:
            continue
        try:
            raw=base64.b64decode(data,validate=True)
        except (ValueError,binascii.Error):
            continue
        if not raw.startswith(b"\xff\xd8\xff"):
            continue
        safe=base64.b64encode(raw).decode("ascii")
        figures.append(f'<figure style="flex:1;min-width:200px;margin:8px 0"><figcaption>{title}</figcaption><img alt="{title} observed viewport" style="width:100%;height:auto;border:1px solid #999" src="data:image/jpeg;base64,{safe}"></figure>')
    return '<div style="display:flex;gap:12px;flex-wrap:wrap">'+''.join(figures)+'</div>' if figures else ""

def without_images(runs):
    return [{k:v for k,v in r.items() if k!="screenshot_jpeg"} for r in runs]
