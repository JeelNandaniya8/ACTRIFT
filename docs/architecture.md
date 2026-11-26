# Architecture

The planner performs bounded breadth-first exploration from baseline actions. Each path is replayed against both versions in fresh Chromium contexts. Repeated observations are compared for stability, then action deltas are compared across versions. Text changes, route changes and download hashes are evidence, not universal specifications.

Earlier versions pruned observable states; the current planner instead explores bounded paths without state pruning, but still cannot exhaust hidden state. Exact accessible names can fail across renames. Server-side state is not reset by browser isolation. Candidate-only actions are inventoried rather than exhaustively explored.

Evidence v1 stores settings, path, classification, reasons and repeated observations. Replay requires the two applications to be running independently.

Observation revision 2 preserves text multiplicity and adds action availability deltas. No-effect journeys are classified as unobserved. Exploration remains bounded; the network filter is not a sandbox and redirect chains may bypass request interception. Off-origin final navigation is treated as inconclusive. Always use external isolation.

Revision 3 captures bounded action-time page errors. Baseline errors are inconclusive; reproducible candidate exceptions against a healthy baseline are reported as behavior changes. Matching suggestions use same-role token normalization, a small synonym table and string similarity, never auto-execution.
