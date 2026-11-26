# Security

This research preview is intended for disposable local test applications with synthetic data. Browser actions may change application state; network filtering is not a security sandbox. Run potentially untrusted applications inside isolated environments without credentials or sensitive network access.

Do not submit secrets, private page content or production credentials in evidence reports. Report vulnerabilities privately through GitHub private vulnerability reporting if enabled; otherwise request a private contact channel without posting exploit details.

Browser request interception is not a complete egress control (including redirect chains and browser subsystems). Do not rely on it to contain an untrusted app. Use OS-level process/network isolation, and never run on a machine with reachable sensitive services. Failed downloads and off-origin final navigation are reported as inconclusive.
