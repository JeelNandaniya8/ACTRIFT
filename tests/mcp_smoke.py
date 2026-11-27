"""Actual stdio round-trip using the optional MCP client SDK."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def smoke():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"evidence.json"
        p.write_text(json.dumps({"schema":"ghostdiff.evidence/v1","observation_revision":3,"paths":[{"path":[],"status":"inventory"},{"path":[{"name":"private label","role":"button"}],"status":"equivalent_observed"}],"summary":{"inventory":1,"equivalent_observed":1},"coverage":{"executed_paths":2,"omitted_budget_branches":0}}),encoding="utf-8")
        params=StdioServerParameters(command=sys.executable,args=["-m","ghostdiff.mcp_server","--evidence",str(p)])
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools=await session.list_tools()
                assert [t.name for t in tools.tools]==["evidence_summary"]
                result=await session.call_tool("evidence_summary",{"strict_policy":True})
                assert not result.isError
                raw=json.loads(result.content[0].text)
                assert raw["exit_code"]==0
                assert "private label" not in result.content[0].text

if __name__=="__main__":asyncio.run(smoke())
