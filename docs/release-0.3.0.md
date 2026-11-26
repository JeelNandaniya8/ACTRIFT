## Reliability and browser portability preview

- More conservative observations: duplicate text counts, action availability changes and explicit unobserved journeys.
- Improved invalid-input, interruption and browser failure handling.
- Browser installation doctor and selectable Chromium, Firefox and WebKit.
- Browser smoke matrix and wheel installation check gate publication.
- Persistent contracts now require observation revision 2. Recreate earlier contracts.

Install the wheel, install your preferred browser with python -m playwright install chromium (or firefox / webkit), and run ghostdiff demo.

This is experimental. Browser smoke coverage is not full cross-platform equivalence; bounded exploration cannot certify every feature. Benchmarks use planted defects, including a pinned upstream example, not historical production defects. Run only against isolated disposable applications.
