# ACTRIFT trusted publishing

The new distribution is `actrift` version 0.8.0. The prior `ghostdiff-lab` 0.7.0 release stays available. Register a new pending trusted publisher at https://pypi.org/manage/account/publishing/. A search result is not a name reservation.

- Project: actrift
- GitHub owner: JeelNandaniya8
- Repository: use the actual current repository name (GHOSTDIFF until the owner renames it to ACTRIFT)
- Workflow: publish-pypi.yml
- Environment: pypi

If the name belongs to another project, stop. Verify the exact main revision, successful Tests and Automated security checks, package ownership and reviewed findings. Publish a new GitHub preview release v0.8.0 with the gated release workflow first, then dispatch the PyPI workflow for that same revision. Restrict the pypi environment to main and use maintainer approval where supported. Never share credentials. See [migration](migration.md). No package availability or successful 0.8.0 publication is claimed yet.
