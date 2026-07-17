# Xsuite Helpers Tests

This folder contains tests for `sad2xs.xsuite_helpers` — Python utilities
that operate purely on an `xt.Line`, independent of SAD. Directly parallel
to `tests/sad_helpers/` testing `sad2xs.sad_helpers`.

This folder is not to be confused with `tests/xtrack/`, which pins down
ground truth about the third-party `xtrack` library itself; these tests
cover sad2xs's own code in `sad2xs.xsuite_helpers`.

## Test harness

Tests build a minimal `xt.Line` directly (no SAD lattice, no sad2xs
conversion) and call the helpers on it.

## Coverage

Does not require the SAD binary.

| File | Functions | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_reference_energy.py` | 14 | 0 | — |
| `test_symplecticity.py` | 4 | 0 | — |
| `test_twiss_assertions.py` | 4 | 0 | — |
| `test_twiss_alignment.py` | 9 | 0 | — |
| `test_comparison_plots.py` | 5 | 0 | — |
