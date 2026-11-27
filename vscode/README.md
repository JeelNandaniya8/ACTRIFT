# ACTRIFT Evidence for VS Code (development preview)

Read-only local editor integration. Open the vscode directory in VS Code, start the extension development host with F5, and run **ACTRIFT: Inspect Local Evidence** in a trusted workspace. Select a ACTRIFT revision-3 evidence JSON file. The Output panel shows a strict verdict, counters, coverage and finding indices.

The extension has no runtime npm dependencies, does not run commands, invoke browsers, start servers, fetch URLs, inspect the workspace automatically, or render observed HTML. It only reads an explicitly selected local file, capped at 32 MiB, and reports data-minimized fixed fields. Evidence may be forged; this is inspection rather than provenance verification.

Run `npm test` with Node.js 20+ (no dependency installation needed). CI runs these tests and retains extension source. Extension-host testing, VSIX packaging, publisher ownership and Marketplace publication are separate milestones; the extension is not yet listed in the Marketplace. Use trusted local evidence.
