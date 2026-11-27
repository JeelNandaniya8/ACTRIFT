# htmx historical out-of-band swap defect

Fixed commit: https://github.com/bigskysoftware/htmx/commit/730bd8224da11628bdd9363baf114325fa30a3b5
Buggy parent: 8409ebca3bad8d67b3f6bcd71bbe614888a73da0. Original upstream src/htmx.js snapshots retained under the upstream license. The separate local integration harness uses the upstream regression test's special-character ID and an HTTP GET response. This is a real library regression exercised in a minimal synthetic application, not a full production deployment.
