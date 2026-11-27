"use strict";
const STATUSES = ["inventory", "equivalent_observed", "behavior_changed", "download_changed", "unmatched", "unobserved", "inconclusive"];
const DIFF = ["behavior_changed", "download_changed", "unmatched"];
const COVERAGE = ["executed_paths", "path_budget", "depth_limit", "omitted_budget_branches", "depth_frontiers", "skipped_action_entries"];
const MAX_BYTES = 32 * 1024 * 1024;
function object(x) { return x !== null && typeof x === "object" && !Array.isArray(x); }
function requireValue(ok) { if (!ok) throw new Error("Invalid or unsupported evidence"); }
function summarize(report, strict = true) {
    requireValue(typeof strict === "boolean" && object(report) && report.schema === "ghostdiff.evidence/v1" && report.observation_revision === 3);
    const rows = report.paths;
    requireValue(Array.isArray(rows) && rows.length >= 1 && rows.length <= 200 && object(report.summary));
    const counts = Object.fromEntries(STATUSES.map(k => [k, 0]));
    const findings = [];
    for (const [index, row] of rows.entries()) {
        requireValue(object(row) && STATUSES.includes(row.status) && Array.isArray(row.path) && row.path.length <= 5);
        counts[row.status]++;
        if (DIFF.includes(row.status) || ["unobserved", "inconclusive"].includes(row.status)) {
            findings.push({ evidence_index: index, status: row.status, depth: row.path.length });
        }
    }
    requireValue(Object.keys(report.summary).length === STATUSES.filter(k => counts[k] > 0).length);
    for (const [key, value] of Object.entries(report.summary)) {
        requireValue(STATUSES.includes(key) && Number.isSafeInteger(value) && value > 0 && counts[key] === value);
    }
    const list = key => {
        const value = Object.hasOwn(report, key) ? report[key] : [];
        requireValue(Array.isArray(value)); return value.length;
    };
    const baselineOnly = list("baseline_only_actions"), candidateOnly = list("candidate_only_actions"), skipped = list("skipped_actions");
    const source = Object.hasOwn(report, "coverage") ? report.coverage : {};
    requireValue(object(source));
    const coverage = {};
    for (const key of COVERAGE) {
        if (Object.hasOwn(source, key)) {
            requireValue(Number.isSafeInteger(source[key]) && source[key] >= 0);
            coverage[key] = source[key];
        }
    }
    requireValue(!Object.hasOwn(coverage, "executed_paths") || coverage.executed_paths === rows.length);
    const code = counts.inconclusive ? 2 : DIFF.some(k => counts[k]) || baselineOnly ? 1 :
        !counts.equivalent_observed || (strict && (!Object.hasOwn(coverage, "omitted_budget_branches") || coverage.omitted_budget_branches || skipped || counts.unobserved)) ? 2 : 0;
    return { schema: "ghostdiff.editor-summary/v1", verdict: ["matched_observations", "differences_observed", "inconclusive"][code], exit_code: code, strict,
        summary: counts, coverage, baseline_only_count: baselineOnly, candidate_only_count: candidateOnly, skipped_count: skipped, findings,
        limits: "Saved evidence only. No provenance verification or guarantee of correctness." };
}
function parseEvidence(buffer) {
    requireValue(Buffer.isBuffer(buffer) && buffer.length <= MAX_BYTES);
    return summarize(JSON.parse(buffer.toString("utf8")), true);
}
module.exports = { summarize, parseEvidence, MAX_BYTES };
