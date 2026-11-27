"""Bounded offline Source Map v3 decoder for explicit local maps."""
from bisect import bisect_right
from pathlib import Path
import json
import re

BASE64="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
VALUES={c:i for i,c in enumerate(BASE64)}
MAX_MAP=2*1024*1024

def vlq(segment):
    numbers=[];value=shift=0
    for c in segment:
        if c not in VALUES:raise ValueError("Invalid source-map VLQ")
        n=VALUES[c];value|=(n&31)<<shift
        if n&32:
            shift+=5
            if shift>30:raise ValueError("Source-map VLQ overflow")
        else:
            numbers.append(-(value>>1) if value&1 else value>>1)
            value=shift=0
    if shift:raise ValueError("Truncated source-map VLQ")
    return numbers

def safe_source(root,source):
    if not isinstance(root,str) or not isinstance(source,str):raise ValueError("Invalid source path")
    s=(root.rstrip("/")+"/" if root else "")+source
    if s.startswith(("/", "\\")) or ":" in s or "\\" in s or any(ord(c)<32 for c in s) or len(s)>400:
        raise ValueError("Only relative source paths supported")
    parts=[]
    for part in s.split("/"):
        if part=="..":
            if parts:parts.pop()
            else:raise ValueError("Source path escapes map root")
        elif part not in ("","."):parts.append(part)
    return "/".join(parts)

class SourceMap:
    def __init__(self,data):
        if not isinstance(data,dict) or data.get("version")!=3 or "sections" in data:raise ValueError("Require ordinary Source Map v3")
        sources=data["sources"];names=data.get("names",[]);mappings=data["mappings"]
        if not isinstance(sources,list) or len(sources)>10000 or not isinstance(names,list) or len(names)>10000 or not isinstance(mappings,str) or len(mappings)>MAX_MAP:
            raise ValueError("Source map exceeds bounds")
        root=data.get("sourceRoot","")
        self.sources=[safe_source(root,s) for s in sources]
        self.names=names;self.lines=[]
        source=original_line=original_col=name=0
        total=0
        for line in mappings.split(";"):
            generated=0;segments=[]
            for segment in line.split(",") if line else []:
                total+=1
                if total>100000:raise ValueError("Too many mapping segments")
                vals=vlq(segment)
                if len(vals) not in (1,4,5) or vals[0]<0:raise ValueError("Invalid source-map segment")
                generated+=vals[0]
                if len(vals)==1:
                    segments.append((generated,None));continue
                source+=vals[1];original_line+=vals[2];original_col+=vals[3]
                if not 0<=source<len(self.sources) or min(original_line,original_col)<0:raise ValueError("Invalid mapped coordinate")
                loc={"path":self.sources[source],"line":original_line+1,"column":original_col+1}
                if len(vals)==5:
                    name+=vals[4]
                    if not 0<=name<len(names):raise ValueError("Invalid mapped name")
                    if isinstance(names[name],str):loc["symbol"]=names[name][:120]
                segments.append((generated,loc))
            self.lines.append(segments)
    def lookup(self,line,column):
        if type(line) is not int or type(column) is not int or not 1<=line<=len(self.lines) or column<1:return None
        segments=self.lines[line-1]
        index=bisect_right([s[0] for s in segments],column-1)-1
        return dict(segments[index][1]) if index>=0 and segments[index][1] is not None else None

def load_maps(manifest_path):
    path=Path(manifest_path).resolve(strict=True)
    if path.stat().st_size>65536:raise ValueError("Map manifest too large")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or set(data)!={"schema","maps"} or data["schema"]!="ghostdiff.source-maps/v1" or not isinstance(data["maps"],dict) or len(data["maps"])>20:
        raise ValueError("Invalid source-map manifest")
    maps={}
    for generated,relative in data["maps"].items():
        if not re.fullmatch(r"/[A-Za-z0-9_./~-]{1,250}",generated) or not isinstance(relative,str) or Path(relative).is_absolute():raise ValueError("Invalid map entry")
        target=(path.parent/relative).resolve(strict=True)
        if not target.is_relative_to(path.parent) or not target.is_file() or target.stat().st_size>MAX_MAP:raise ValueError("Map must be a bounded local file within manifest directory")
        maps[generated]=SourceMap(json.loads(target.read_text(encoding="utf-8")))
    return maps

def map_locations(locations,maps):
    mapped=[]
    for loc in locations:
        source_map=maps.get(loc.get("path"))
        original=source_map.lookup(loc.get("line"),loc.get("column")) if source_map else None
        if original:mapped.append({**original,"generated":loc})
    return mapped
