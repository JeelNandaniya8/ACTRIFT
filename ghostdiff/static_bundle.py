"""Bounded static-site interchange for an operator-managed, network-disabled runner.

Packing reads trusted synthetic fixtures only. Running serves validated bytes in
memory, without extraction, shell execution, external URLs or arbitrary config.
This module does not establish OS-level isolation by itself.
"""
import argparse
import base64
import binascii
import json
import re
import sys
from pathlib import Path

from .agent import summarize
from .engine import Settings,compare
from .gitintel import serve_assets

SCHEMA="ghostdiff.static-bundle/v1"
MAX_FILE=2*1024*1024
MAX_SITE=16*1024*1024
MAX_FILES=200
MAX_INPUT=48*1024*1024
EXTENSIONS={".html",".htm",".js",".mjs",".css",".json",".svg",".png",".jpg",".jpeg",".gif",".webp",".ico",".woff",".woff2",".ttf",".txt",".wasm"}
NAME=re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*)*")

def validate_name(name):
    if not isinstance(name,str) or len(name)>240 or not NAME.fullmatch(name):
        raise ValueError("Unsupported asset path")
    if Path(name).suffix.lower() not in EXTENSIONS:
        raise ValueError("Unsupported asset extension")
    return name

def pack_site(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Select a real trusted static-site directory")
    root=root.resolve()
    files={};total=0
    # Do not follow directory symlinks or read hidden paths.
    import os
    for directory,dirs,names in os.walk(root,followlinks=False):
        dirs.sort();names.sort()
        for name in dirs:
            p=Path(directory)/name
            if p.is_symlink() or not NAME.fullmatch(name):
                raise ValueError("Unsupported directory or symlink")
        for name in names:
            p=Path(directory)/name
            key=validate_name(p.relative_to(root).as_posix())
            if p.is_symlink() or not p.is_file():
                raise ValueError("Only regular static assets are accepted")
            if len(files)>=MAX_FILES or p.stat().st_size>MAX_FILE:
                raise ValueError("Static asset limit exceeded")
            with p.open("rb") as stream:
                content=stream.read(MAX_FILE+1)
            total+=len(content)
            if len(content)>MAX_FILE or total>MAX_SITE:
                raise ValueError("Static site byte limit exceeded")
            files[key]=base64.b64encode(content).decode("ascii")
    if "index.html" not in files:
        raise ValueError("Static site requires index.html")
    return files

def decode_site(files):
    if not isinstance(files,dict) or not 1<=len(files)<=MAX_FILES or "index.html" not in files:
        raise ValueError("Invalid static site inventory")
    decoded={};total=0
    for name,encoded in files.items():
        validate_name(name)
        if not isinstance(encoded,str) or len(encoded)>4*((MAX_FILE+2)//3):
            raise ValueError("Invalid encoded asset")
        try:
            content=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error) as exc:
            raise ValueError("Invalid base64 asset") from exc
        total+=len(content)
        if len(content)>MAX_FILE or total>MAX_SITE:
            raise ValueError("Static site byte limit exceeded")
        decoded[name]=content
    return decoded

def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError("Duplicate bundle key")
        result[key]=value
    return result

def parse_bundle(raw):
    if len(raw)>MAX_INPUT:
        raise ValueError("Static bundle exceeds input limit")
    data=json.loads(raw.decode("utf-8"),object_pairs_hook=_unique_pairs)
    if not isinstance(data,dict) or set(data)!={"schema","before","after"} or data["schema"]!=SCHEMA:
        raise ValueError("Unsupported static bundle schema")
    return decode_site(data["before"]),decode_site(data["after"])

def run_bundle(raw,depth=1,budget=8,strict=False):
    before,after=parse_bundle(raw)
    cfg=Settings(depth=depth,budget=budget,repeats=2,settle_ms=250)
    cfg.validate()
    with serve_assets(before) as a,serve_assets(after) as b:
        report=compare(a,b,cfg)
    return summarize(report,strict)

def main(argv=None):
    parser=argparse.ArgumentParser(prog="python -m ghostdiff.static_bundle")
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("pack")
    p.add_argument("--before",required=True);p.add_argument("--after",required=True)
    p=sub.add_parser("compare")
    p.add_argument("--allow-actions",action="store_true")
    p.add_argument("--depth",type=int,default=1,choices=(1,2,3))
    p.add_argument("--budget",type=int,default=8)
    p.add_argument("--strict",action="store_true")
    args=parser.parse_args(argv)
    if args.command=="pack":
        try:
            data={"schema":SCHEMA,"before":pack_site(args.before),"after":pack_site(args.after)}
            print(json.dumps(data,separators=(",",":")))
            return 0
        except (OSError,ValueError):
            print("ghostdiff: invalid or oversized static fixture",file=sys.stderr)
            return 2
    try:
        if not args.allow_actions or not 1<=args.budget<=30:
            raise ValueError("Explicit authorization and bounded budget required")
        result=run_bundle(sys.stdin.buffer.read(MAX_INPUT+1),args.depth,args.budget,args.strict)
        print(json.dumps(result,sort_keys=True))
        return result["exit_code"]
    except KeyboardInterrupt:
        print(json.dumps({"schema":"ghostdiff.agent-result/v1","execution_status":"interrupted","exit_code":130}))
        return 130
    except Exception:
        # Do not echo browser errors, paths or input data into automation logs.
        print(json.dumps({"schema":"ghostdiff.agent-result/v1","execution_status":"error","exit_code":2,"reason":"Invalid bundle, missing authorization or execution failure"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
