# Benchmarks

Run `python benchmarks/run.py` after installing the package and Chromium. The harness measures three labeled planted regressions against a clean redesign, saves machine-readable results, and fails on missed expected findings, clean-control differences or inconclusive journeys.

These are synthetic fixtures. They are not evidence of accuracy on arbitrary applications. For real-world evaluation, select publicly documented historical bugs, pin exact baseline/candidate commits, run disposable apps with synthetic state, define expected outcomes before testing, and publish evidence and all failures. No real-world score has yet been established.

A second historical example, the MDN missing-MessagePort fix, is exercised by `python benchmarks/channel_history.py`. The original buggy and fixed files are preserved; a separate local harness supplies the trigger. CI checks both the historical defect and fixed-versus-fixed control. Both historical examples are small upstream demos, not a production-scale corpus.

`python benchmarks/todomvc_history.py` exercises a documented historical VanillaJS TodoMVC bug against pinned upstream source and a fixed-versus-fixed control. It uses synthetic storage and an explicitly specified two-step journey. `python benchmarks/scale.py` records wall time, coverage and verdict agreement for wide synthetic pages. Neither suite represents production SaaS coverage.

`python benchmarks/todomvc_scale.py` runs the historical TodoMVC regression and two controls for each of 100 and 1,000 synthetic stored tasks. It reports exact expected/observed verdicts and wall time and retains repeated evidence. The historical multi-file application is real upstream source, but its data and execution environment are synthetic. This is large-state validation, not production-scale deployment validation.
