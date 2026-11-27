"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { summarize, parseEvidence } = require("../summary");
const { readBounded } = require("../extension");
function evidence(status = "equivalent_observed") {
    return { schema: "ghostdiff.evidence/v1", observation_revision: 3,
        paths: [{ status: "inventory", path: [] }, { status, path: [{ name: "synthetic-secret-label" }], before: [{ text: "synthetic-secret-content" }] }],
        summary: { inventory: 1, [status]: 1 }, coverage: { executed_paths: 2, omitted_budget_branches: 0 } };
}
test("strict clean, changed and inconclusive verdicts", () => {
    assert.equal(summarize(evidence()).exit_code, 0);
    assert.equal(summarize(evidence("behavior_changed")).exit_code, 1);
    assert.equal(summarize(evidence("unmatched")).exit_code, 1);
    assert.equal(summarize(evidence("inconclusive")).exit_code, 2);
    assert.equal(summarize(evidence("unobserved")).exit_code, 2);
    const omitted = evidence(); omitted.coverage.omitted_budget_branches = 1;
    assert.equal(summarize(omitted).exit_code, 2);
    assert.equal(summarize(omitted, false).exit_code, 0);
});
test("only fixed data-minimized output fields", () => {
    const result = summarize(evidence("download_changed"));
    assert.deepEqual(result.findings, [{ evidence_index: 1, status: "download_changed", depth: 1 }]);
    assert.ok(!JSON.stringify(result).includes("synthetic-secret"));
});
test("reject invalid schema, inconsistent counts, invalid coverage and malformed JSON", () => {
    const a = evidence(); a.summary.equivalent_observed = 9;
    assert.throws(() => summarize(a));
    const b = evidence(); b.coverage.omitted_budget_branches = -1;
    assert.throws(() => summarize(b));
    const c = evidence(); c.observation_revision = 2;
    assert.throws(() => summarize(c));
    assert.throws(() => parseEvidence(Buffer.from("{")));
});
test("selected regular file is read locally and parsed", async () => {
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), "ghostdiff-editor-"));
    try {
        const file = path.join(dir, "evidence.json");
        await fs.writeFile(file, JSON.stringify(evidence()));
        assert.equal(parseEvidence(await readBounded(file)).exit_code, 0);
        await assert.rejects(readBounded(dir));
    } finally { await fs.rm(dir, { recursive: true, force: true }); }
});
