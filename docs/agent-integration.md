# Agent and automation integration

ACTRIFT does not require a model service. A human developer or an agent with local command execution can use the same deterministic policy interface. The integration is a CLI/JSON contract, not an installed third-party connector or hosted MCP server.

Offline inspection:

```sh
actrift agent-summary ghostdiff-report/evidence.json --strict
```

Explicitly authorized execution against independently disposable local fixtures:

```sh
actrift agent-run examples/agent.json --allow-actions
```

Review the config and replace both URLs with actual fixture origins. Agent execution accepts the read-policy config only, excludes screenshots and reverse exploration, never enables backend reset or write-mode flags, and requires explicit authorization. Browser activity may still mutate local state through GET or client-side code. Use disposable synthetic data and OS isolation.

The command emits a single JSON result with schema ghostdiff.agent-result/v1. Exit 0 means observed agreement under the selected policy; 1 means observed differences; 2 means inconclusive or execution error; 130 means interrupted. Findings refer to zero-based evidence row indices and depth, not inferred source causes. Strict mode additionally rejects budget omissions, skipped actions and unobserved paths.

The summary contains fixed status strings, counters and indices only, not raw page content, URLs, selectors, labels, exception messages, API digests or screenshots. Raw evidence is not persisted unless --evidence-out is explicitly provided. That file may contain sensitive data; never feed it to an agent without review. A malicious or forged input report can still misrepresent results; schema and counter validation is not provenance verification.

An agent should present uncertainty instead of treating exit 0 as universal correctness, and never re-run a destructive action merely because evidence suggests a regression.
