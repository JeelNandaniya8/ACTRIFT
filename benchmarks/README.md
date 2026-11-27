# Benchmarks

Run `python benchmarks/run.py` after installing the package and Chromium. The harness measures three labeled planted regressions against a clean redesign, saves machine-readable results, and fails on missed expected findings, clean-control differences or inconclusive journeys.

These are synthetic fixtures. They are not evidence of accuracy on arbitrary applications. For real-world evaluation, select publicly documented historical bugs, pin exact baseline/candidate commits, run disposable apps with synthetic state, define expected outcomes before testing, and publish evidence and all failures. No real-world score has yet been established.

A second historical example, the MDN missing-MessagePort fix, is exercised by `python benchmarks/channel_history.py`. The original buggy and fixed files are preserved; a separate local harness supplies the trigger. CI checks both the historical defect and fixed-versus-fixed control. Both historical examples are small upstream demos, not a production-scale corpus.
