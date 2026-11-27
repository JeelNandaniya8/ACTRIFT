# GitHub Action

Use on a Linux runner after starting disposable baseline and candidate applications on separate loopback ports. Pin the action to an audited commit SHA rather than a moving branch.

```yaml
- uses: JeelNandaniya8/GHOSTDIFF@<reviewed-commit-sha>
  with:
    before: http://127.0.0.1:3000
    after: http://127.0.0.1:3001
    upload-report: 'true'
```

The action writes counts to the GitHub job summary and fails on observed changes or inconclusive results under the CLI exit policy. Artifact upload is opt-in, because reports may contain application data. It does not request PR write permission, does not execute fork code in a privileged pull_request_target workflow, and does not automatically create PR comments. Use normal pull_request CI with minimal permissions. Never expose test credentials to untrusted fork code.

## Optional PR comment

The action emits a fixed-label numeric summary. If a maintainer explicitly grants pull-request write permission, add a separate step after the check. For same-repository PRs only:

```yaml
- uses: actions/github-script@v7
  if: always() && github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository
  env:
    GHOSTDIFF_SUMMARY: ${{ steps.ghostdiff.outputs.summary }}
  with:
    script: |
      const text = process.env.GHOSTDIFF_SUMMARY || 'No complete report';
      await github.rest.issues.createComment({
        owner: context.repo.owner, repo: context.repo.repo,
        issue_number: context.issue.number,
        body: 'GHOSTDIFF observed results: ' + text
      });
```

The preceding comparison step must have id: ghostdiff. Use a trusted workflow and minimal permissions; comments require pull-requests: write and a token permitted to comment. Do not execute untrusted candidate code in a privileged pull_request_target workflow. The main action never requests write access. The example is not enabled automatically.

Set `require-complete: 'true'` to reject budget-omitted, skipped and unobserved journeys in addition to observed changes. The action uses summary-only console output by default; artifacts still contain raw evidence and remain opt-in. Coverage counts are reported in the job summary. Stable baseline-only action inventory entries fail the default gate even when the relevant path was not executed.
