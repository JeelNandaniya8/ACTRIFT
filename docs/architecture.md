# Architecture

The planner performs bounded breadth-first exploration from baseline actions. Each path is replayed against both versions in fresh Chromium contexts. Repeated observations are compared for stability, then action deltas are compared across versions. Text changes, route changes and download hashes are evidence, not universal specifications.

State pruning uses observable snapshots and can miss hidden state. Exact accessible names can fail across renames. Server-side state is not reset by browser isolation. Candidate-only actions are inventoried rather than exhaustively explored.

Evidence v1 stores settings, path, classification, reasons and repeated observations. Replay requires the two applications to be running independently.
