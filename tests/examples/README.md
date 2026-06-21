# Example Tests

This folder contains tests for public examples and example lattices.

These tests should protect examples that users may copy or run directly. Keep
example-specific assertions here; shared converter, parser, writer, or helper
contracts belong in their dedicated folders.

Public example tests consume the committed assets under `examples/`. Synthetic
example lattices that exist only to exercise example-style full-lattice shapes
live under `tests/examples/lattices/`.

## Coverage

- `test_example_lattices.py` (1 test, 3 parametrized instances) — conversion
  smoke tests for synthetic FCC-style lattices (`fcc_h_dummy.sad`,
  `fcc_tt_coll_dummy.sad`, `fcc_sol_dummy.sad`). Checks that each converts to
  an `xt.Line` with `start`/`end` markers and a reference particle.

- `test_public_examples.py` (3 tests) — covers the full public example
  workflow:
  - Conversion smoke test: 3 committed example lattices (`fccee_zh.sad`,
    `fccee_tt_collimation.sad`, `fccee_sol.sad`) convert to a non-empty
    `xt.Line` with a reference particle (1 parametrized test, 3 instances).
  - Write and reload: the same 3 lattices are converted, written with
    `write_lattice` and `write_optics`, reloaded in a fresh Xsuite environment,
    and checked for a non-empty line and reference particle. This exercises the
    full workflow a user follows when running the committed examples
    (1 parametrized test, 3 instances).
  - Script contract: each of the 4 public example scripts is committed, its
    referenced lattice file exists, and the lattice filename appears verbatim
    in the script content (1 test).
