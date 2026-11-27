"""Explicit CI policy for observed differences and incomplete exploration."""

def exit_code(report, strict=False):
    summary=report["summary"]
    if summary.get("inconclusive"):
        return 2
    if any(summary.get(k) for k in ("unmatched","behavior_changed","download_changed")):
        return 1
    if report.get("baseline_only_actions"):
        return 1
    if not summary.get("equivalent_observed"):
        return 2
    if strict:
        coverage=report.get("coverage",{})
        if "omitted_budget_branches" not in coverage:
            return 2
        if coverage["omitted_budget_branches"] or report.get("skipped_actions") or summary.get("unobserved"):
            return 2
    return 0
