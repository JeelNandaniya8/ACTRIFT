# PyPI release with trusted publishing

The package distribution name is ghostdiff-lab. Ownership and availability on PyPI must be confirmed by the maintainer; no name reservation or publication is implied.

After the exact main commit passes Tests and Automated security checks and the maintainer reviews the findings, publish the matching GitHub preview release. Configure a trusted publisher in your own PyPI account (pending publisher for a new project): https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/

- PyPI project name: ghostdiff-lab
- Repository owner: JeelNandaniya8
- Repository: GHOSTDIFF
- Workflow: publish-pypi.yml
- GitHub environment: pypi

Restrict the GitHub environment to main and configure maintainer approval where supported. Run Publish verified package to PyPI from GitHub Actions with the exact commit and successful test/security run IDs, confirming review only after actually reviewing results. The workflow checks the matching published GitHub release tag, validates the CI artifact checksums and passes the checked distributions to a separate OIDC publishing job. No long-lived API token is required. Do not share credentials. If the package name belongs to another maintainer, stop rather than publishing under that identity.

Official instructions: https://docs.pypi.org/trusted-publishers/using-a-publisher/
