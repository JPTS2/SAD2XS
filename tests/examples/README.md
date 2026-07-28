# Example Tests

This folder contains tests for public examples and example lattices.

These tests should protect examples that users may copy or run directly. Keep
example-specific assertions here; shared converter, parser, writer, or helper
contracts belong in their dedicated folders.

Public example tests consume the committed assets under `examples/`. Synthetic
example lattices that exist only to exercise example-style full-lattice shapes
live under `tests/examples/lattices/`.

## Coverage

- `test_example_lattices.py` (3 tests) — conversion
  smoke tests for synthetic FCC-style lattices (`fcc_h_dummy.sad`,
  `fcc_tt_coll_dummy.sad`, `fcc_sol_dummy.sad`). Checks that each converts to
  an `xt.Line` with `start`/`end` markers and a reference particle.

- `test_public_examples.py` (14 tests) — covers the full public example
  workflow. Committed example lattices are auto-discovered from
  `examples/lattices/*.sad` (excluding `*_rebuilt.sad`), currently
  `fccee_zh.sad`, `fccee_tt_collimation.sad`, `fccee_sol.sad`, and
  `fccee_coupled.sad`:
  - Conversion smoke test: each discovered lattice converts to a non-empty
    `xt.Line` with a reference particle (1 parametrized test, one instance per
    lattice).
  - Write and reload: the same lattices are converted, written with
    `write_lattice` and `write_optics`, reloaded in a fresh Xsuite environment,
    and checked for a non-empty line and reference particle. This exercises the
    full workflow a user follows when running the committed examples
    (1 parametrized test, one instance per lattice).
  - Script execution: each numbered public example script under `examples/`
    is run headlessly with `SHOW_PLOTS=False`, a temporary output directory,
    and the example's own assertions enabled (1 parametrized test).
  - Script contract: each numbered public example script references at least
    one committed lattice file under `examples/lattices` (1 test).

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
