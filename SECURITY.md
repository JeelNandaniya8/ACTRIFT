# Security

This research preview is intended for disposable local test applications with synthetic data. Browser actions may change application state; network filtering is not a security sandbox. Run potentially untrusted applications inside isolated environments without credentials or sensitive network access.

Do not submit secrets, private page content or production credentials in evidence reports. Report vulnerabilities privately through GitHub private vulnerability reporting if enabled; otherwise request a private contact channel without posting exploit details.

Browser request interception is not a complete egress control (including redirect chains and browser subsystems). Do not rely on it to contain an untrusted app. Use OS-level process/network isolation, and never run on a machine with reachable sensitive services. Failed downloads and off-origin final navigation are reported as inconclusive.

The optional container recipe disables networking during the bundled demo and uses a non-root account and resource limits. It is not a certified sandbox; a dedicated disposable VM remains recommended for untrusted code.

Storage-state JSON may contain credentials. Never commit or upload it. Optional screenshots and captured text may contain sensitive application data. The default risky-action name filter is a heuristic and cannot prevent all destructive effects; keep using disposable isolated fixtures.

Explicit synthetic form journeys retain the default network and action restrictions. Password-like field detection is heuristic, not a guarantee. Session state is scoped to the target local origin and cookie host. Do not supply secrets or real user information.

The engine also flags observed off-origin HTTP responses as inconclusive. This is a detection backstop, not prevention: a request may already have reached another origin (including redirects). Security regression tests check direct off-origin fetch blocking, default POST blocking and HTML report escaping. They are not an independent security audit.

Automated security CI uses pip-audit for known dependency vulnerabilities and Bandit to produce a static-source review report. Scanner output must be reviewed; absence of findings is not proof of safety. Parallel mode uses two independent browsers and forbids write-enabled sessions, but callers must ensure the backends are truly independent.

Observation resource limits: 5,000 candidate DOM elements, 256 unique named actions, 20 sampled errors per type, 8 download events and 20 MiB aggregate download hashing per step. Exceeding relevant limits yields inconclusive rather than verified results. These are bounded observation safeguards, not network, disk, memory or process isolation; downloads may already have consumed disk before checks, and an application can still exhaust browser resources. Run in disposable OS-level isolation.

The optional reset protocol intentionally sends a POST to a fixed endpoint on explicitly authorized numeric-loopback HTTP test servers. It does not follow redirects, requires a 204 receipt, and is disabled by default. Never enable it on production infrastructure. See docs/backend-reset.md.
