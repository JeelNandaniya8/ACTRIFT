# Contributing

Create a virtual environment, install the package with pip install -e ., install Chromium with python -m playwright install chromium, and run python -m unittest discover -s tests -v. Set GHOSTDIFF_BROWSER_TESTS=1 to include browser tests.

For new detection logic, include a broken fixture and a clean control. Explain how the evidence is reproduced and which cases remain ambiguous. Do not label unmatched actions as definitively removed without additional evidence.

Keep reports free of private data, and use disposable test applications only.
