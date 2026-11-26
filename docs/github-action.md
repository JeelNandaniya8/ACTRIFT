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
