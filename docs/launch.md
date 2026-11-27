# Public preview launch kit

Publish after the current CI and package artifact are verified. The original and expanded Chromium workflows passed; Firefox and WebKit smoke tests passed on the 0.3 development revision. Do not present earlier verification as proof of the latest revision. Automatic release creation returned HTTP 403; maintainers can create the release from a verified distribution artifact.

## Show HN

Title: Show HN: Ghostdiff – compare browser behavior, not source code

Git diffs don't tell me whether a button still works. Ghostdiff explores short user journeys across two disposable local web apps, compares observable outcomes and freezes repeatable baseline observations into regression contracts. It is experimental and open source. I'm interested in feedback on ambiguous matches and reproducible historical web defects.

https://github.com/JeelNandaniya8/GHOSTDIFF

## X

Git diff shows code changes. Ghostdiff investigates behavior changes. Compare two local web apps, inspect repeatable evidence, and freeze observed journeys into regression contracts. Experimental, open source, no required model API.

https://github.com/JeelNandaniya8/GHOSTDIFF

## Reddit

I am working on Ghostdiff, a local-first browser behavior comparison experiment. It compares observable action outcomes, including downloads and exceptions, and can save stable baseline observations as regression contracts. I'd appreciate feedback and reproducible historical web bugs to extend its benchmark. This isn't a claim that every feature can be automatically tested.

https://github.com/JeelNandaniya8/GHOSTDIFF

## Distribution

- Verify CI at https://github.com/JeelNandaniya8/GHOSTDIFF/actions.
- Download the distribution artifact from the passing run.
- Create a prerelease as a maintainer at https://github.com/JeelNandaniya8/GHOSTDIFF/releases/new.
- Submit via https://news.ycombinator.com/submit and https://www.reddit.com/submit or https://x.com/compose/post from the owner's authenticated accounts; follow community rules, disclose experimental limitations, never manufacture engagement.

Publication requires authenticated account access and a verified latest distribution. No social announcement or release is implied by this document.

For v0.5.0 onward, use the maintainer-controlled [Publish verified preview workflow](https://github.com/JeelNandaniya8/GHOSTDIFF/actions/workflows/publish-preview.yml) only after the exact main commit has passed the Tests and Automated security checks workflows and security findings have been reviewed. If GitHub denies release permission, the owner can manually publish the verified wheel, source distribution and SHA256SUMS from the corresponding CI artifact.

## v0.6.0 launch draft (publish only after exact-revision verification)

Show HN: GHOSTDIFF – Git diff for observed browser behavior

GHOSTDIFF compares disposable local versions of a web app, finds repeatable differences, freezes observable regression contracts, and now offers behavior fingerprints, review-only rename hypotheses and a regression boundary search over locally provisioned revisions. The project includes pinned historical examples and synthetic clean controls. I'm looking for reproducible bugs and independent review. It is an experimental tool, not a guarantee of correctness or an audited sandbox.

Repository: https://github.com/JeelNandaniya8/GHOSTDIFF

Demo recording sequence: run the planted demo, open the report, show the PDF failure, inspect the diagnosis, freeze the baseline and show the fingerprint. Record an actual run, not a fabricated result. No social post has been published by this document.

For the 0.7.0 preview, show an actual local Git snapshot bisect with a disposable example, then compare a source-localization report. State that only static snapshots are automatically provisioned and that candidate hunks are hypotheses. Use exact-revision verification and the maintainer-controlled release workflow before announcing the new package.
