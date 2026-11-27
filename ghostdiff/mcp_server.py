"""Optional local stdio MCP server. Fixed inputs are selected by the operator."""
import argparse
import json
from pathlib import Path
from .agent import summarize

def load_report(path):
    if path.stat().st_size>32*1024*1024:raise ValueError("Evidence too large")
    return json.loads(path.read_text(encoding="utf-8"))

def create_server(evidence):
    from mcp.server.fastmcp import FastMCP
    # Freeze the data-minimized result at startup. No file paths or URLs accepted from tools.
    report=load_report(Path(evidence))
    normal=summarize(report)
    strict=summarize(report,True)
    server=FastMCP("GHOSTDIFF")
    @server.tool()
    def evidence_summary(strict_policy: bool=False) -> dict:
        """Return bounded verdicts and counters from the operator-selected local report."""
        return strict if strict_policy else normal
    return server

def main(argv=None):
    p=argparse.ArgumentParser(prog="ghostdiff-mcp")
    p.add_argument("--evidence",required=True,help="Operator-selected evidence JSON")
    args=p.parse_args(argv)
    create_server(args.evidence).run(transport="stdio")

if __name__=="__main__":main()
