# Security review checklist (maintainer self-review)

Scope: local disposable synthetic applications. Trust boundary: browser, local app, operating system, test configuration, stored credentials and evidence files.

| Control | Verification | Residual limitation |
|---|---|---|
| Default write-method block | Browser test checks no POST reaches fixture | GET can mutate data; redirects can bypass routing |
| Direct cross-origin request block | Browser test checks second local origin receives no probe | Not comprehensive egress enforcement |
| Off-origin response detection | Engine records unexpected response as inconclusive | Does not prevent the request |
| HTML report escaping | Unit test with markup-like evidence | Evidence may contain sensitive data |
| Network-disabled demo container | CI executes historical fixture | Not audited against container escapes |
| Local storage state scope | Origin and cookie-host checks | Cookies may be sensitive; host scope is not port isolation |

Independent review, dedicated VM isolation, production data handling, resource exhaustion testing and comprehensive browser network analysis remain open. Never present these checks as certification.

Additional automated checks: pip-audit against the installed application dependencies and a Bandit source scan. Inspect the security workflow artifacts and triage findings before release. These tools are third-party scanners, not a third-party human audit. No independent auditor has been engaged.

A bounded-observation review adds resource-limit regression tests for excess named controls and error floods, plus bounded event samples and aggregate download hashing. These are not full denial-of-service controls. A public request for independent review is tracked in the repository; only an actual independent reviewer can complete it. The security CI publishes Bandit counts by severity/confidence/rule for triage, with raw findings retained in its artifact.

The optional MCP dependency set is included in the Python vulnerability scan. The stdio server exposes fixed counters from an operator-selected report; tool calls accept no paths, URLs or commands. Source maps and local history remain trusted local inputs. Independent review is still required.

Static fixture interchange is bounded, rejects traversal/hidden paths and symlink packing, and performs no extraction or build execution. CI exercises clean and changed static fixtures with no host mounts or network. Source diff paths use literal pathspecs. These are defensive regression checks, not a claim of containment against hostile browser code.
