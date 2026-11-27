"use strict";
const fs = require("node:fs/promises");
const { parseEvidence, MAX_BYTES } = require("./summary");

async function readBounded(file) {
    const handle = await fs.open(file, "r");
    try {
        const stat = await handle.stat();
        if (!stat.isFile() || stat.size > MAX_BYTES) throw new Error("Unsupported input");
        const buffer = Buffer.alloc(stat.size + 1);
        let offset = 0;
        while (offset < buffer.length) {
            const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset, offset);
            if (!bytesRead) break;
            offset += bytesRead;
        }
        const after = await handle.stat();
        if (offset !== stat.size || after.size !== stat.size || after.mtimeMs !== stat.mtimeMs) throw new Error("Input changed");
        return buffer.subarray(0, offset);
    } finally {
        await handle.close();
    }
}

function activate(context) {
    const vscode = require("vscode");
    const channel = vscode.window.createOutputChannel("ACTRIFT Evidence");
    context.subscriptions.push(channel, vscode.commands.registerCommand("actrift.openEvidence", async () => {
        if (!vscode.workspace.isTrusted) {
            vscode.window.showWarningMessage("ACTRIFT requires a trusted workspace.");
            return;
        }
        const selected = await vscode.window.showOpenDialog({ canSelectFiles: true, canSelectFolders: false, canSelectMany: false, filters: { "Evidence JSON": ["json"] }, openLabel: "Inspect evidence" });
        if (!selected || selected.length !== 1 || selected[0].scheme !== "file") return;
        try {
            const summary = parseEvidence(await readBounded(selected[0].fsPath));
            channel.clear();
            channel.appendLine("ACTRIFT — strict observed-evidence summary");
            channel.appendLine(JSON.stringify(summary, null, 2));
            channel.show(true);
            vscode.window.showInformationMessage("ACTRIFT: " + summary.verdict.replaceAll("_", " "));
        } catch {
            vscode.window.showErrorMessage("ACTRIFT: invalid, oversized, changed or unreadable evidence file.");
        }
    }));
}
module.exports = { activate, readBounded };
