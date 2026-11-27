# Local MCP server (optional)

Python 3.11+ and `pip install '.[mcp]'` enable the stdio server using the official Python SDK v1. See https://py.sdk.modelcontextprotocol.io/v1/. No hosted endpoint or model API is needed.

Configure your MCP host with command `ghostdiff-mcp` and arguments `--evidence /absolute/path/to/evidence.json`. The server exposes only the evidence_summary tool, returning fixed counters and statuses from the operator-selected report captured at startup. It accepts no arbitrary file paths, URLs, commands, browser actions or raw evidence export from tool calls. Restart to change reports. Active testing remains in the separately authorized CLI. The MCP smoke test initializes a real stdio client, lists tools and calls the summary.

This is a local read-only integration; it is not a hosted connector or an audited security boundary.
