# Xsuite Ground-Truth Tests

This folder contains empirical tests that verify what the third-party `xtrack` library
actually does at runtime, as opposed to SAD (`tests/sad/`) or sad2xs's own conversion
logic. They exist to pin down xtrack behaviour that sad2xs's converter or its
documentation relies on, so that an upstream xtrack change is caught rather than
silently invalidating an assumption baked into sad2xs.

## Motivation

sad2xs warns that its Xsuite `Cavity` elements do not model the transverse RF-focusing
kick that SAD's own tracking applies whenever `RFSW` is on and `VOLT != 0`
(Rosenzweig & Serafini, *Phys. Rev. E* **49**, 1599 (1994); see
`docs/reference/sad-behaviour.md`). That claim is a statement about `xtrack`, not about sad2xs's
own code, so it needs its own ground-truth test rather than being asserted from memory
or from reading the source once. If xtrack ever adds this term, this test fails loudly
and the warning (and the docs entry) need revisiting.

The same applies to xtrack behaviour that sad2xs's own defaults rest on: the `adaptive`
model resolving to the expanded map, and yoshida4 batching kicks in groups of seven. Both
are the stated reasons for choices in `docs/converter/models-integrators.md`.

## Test harness

Tests build a minimal `xt.Line` directly (no SAD lattice, no sad2xs conversion) and
track particles through it, asserting on the resulting coordinates.

## Coverage

Does not require the SAD binary.

| File | Tests | Fail | Failure root cause |
|------|-----------|------|--------------------|
| `test_cavity.py` | 2 | 0 | — |
| `test_model_defaults.py` | 7 | 0 | — |

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
