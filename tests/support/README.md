# Test Support

This folder contains reusable support modules for the test suite.

Support modules should make tests clearer without hiding the behaviour under
test. Keep shared constants, diagnostic writers, and small assertion helpers
here.

Files in this folder are not test modules. They should be safe to import and
should not run SAD, perform assertions, or have side effects at import time.

## Modules

| File | Purpose |
|------|---------|
| `config.py` | Shared numeric tolerances (`DELTA_*_ATOL/RTOL`) and parametrisation arrays (`TEST_VALUES`) used across conversion and parser tests |
| `diagnostics.py` | Diagnostic report writers invoked by failing physics-equivalence tests to produce readable `.md` artefacts under `tests/artifacts/` |
| `known_issues.py` | Central test-node to GitHub-issue mapping used by the regression and known-issue CI selections |
| `lattices.py` | Shared SAD lattice-writing helpers for SAD helper tests: `write_minimal_transfer_lattice`, `write_minimal_bend_lattice`, `write_fodo_ring` |
