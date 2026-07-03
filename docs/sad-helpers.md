# SAD helpers

The `sad2xs.sad_helpers` package contains Python wrappers around external SAD calculations.

These helpers are separate from the core SAD-to-Xsuite converter. They are used for comparison, validation, and workflows where SAD remains useful alongside the converted Xsuite model.

`sad2xs.sad_helpers` is lazily imported, so a bare `import sad2xs` does not require its dependencies. Install them with:

```
pip install sad2xs[sad_helpers]
```

## Requirements

The helper functions require:

- a working SAD executable — this is not pip-installable and must be installed/licensed separately;
- input lattice files that SAD can read;
- the `sad_helpers` extra (`tfs-pandas`, `tqdm`), plus `numpy` and `xtrack` from the core dependencies;
- a writable current working directory for temporary command and output files.

By default the helpers call an executable named `sad`. A different executable path can be passed with the `sad_path` argument.

## Public helper functions

The following functions are re-exported from `sad2xs.sad_helpers`:

- `rebuild_sad_lattice`: load a SAD lattice, optionally apply additional SAD commands, and write a rebuilt SAD file.
- `twiss_sad`: run SAD Twiss and return an Xsuite-style `TwissTable`.
- `survey_sad`: run SAD survey-style output and return an Xsuite-style survey table.
- `emit_sad`: run SAD emittance calculation and return parsed emittance information.
- `track_sad`: track particles in SAD and return particle coordinates.
- `transfer_matrix_sad`: compute a SAD transfer matrix for a full line or an element range.
- `chromaticity_sad`: scan off-momentum tunes and fit chromaticities.
- `compute_chromatic_functions`: compute chromatic functions by finite differences around a SAD Twiss calculation.
- `compute_second_order_dispersions`: compute second-order dispersions by finite differences around a SAD Twiss calculation.

## Typical use from Python

```python
from sad2xs.sad_helpers import twiss_sad, track_sad

tw = twiss_sad(
    lattice_filepath="path/to/lattice.sad",
    line_name="RING",
    closed=True,
    wall_time=60,
    sad_path="sad",
)
```

Tracking uses NumPy arrays for the initial particle coordinates:

```python
import numpy as np
from sad2xs.sad_helpers import track_sad

result = track_sad(
    lattice_filepath="path/to/lattice.sad",
    line_name="RING",
    x_init=np.array([0.0]),
    px_init=np.array([0.0]),
    y_init=np.array([0.0]),
    py_init=np.array([0.0]),
    zeta_init=np.array([0.0]),
    delta_init=np.array([0.0]),
    n_turns=10,
    wall_time=120,
    sad_path="sad",
)
```

## Beta-function conventions in coupled regions (e.g. solenoids)

SAD's `twiss_sad` output (`betx`/`bety`/`alfx`/`alfy`) reports the *projected*
(physical) beam-envelope optics functions — the quantity a beam-size monitor
would actually see, correctly combining both normal-mode contributions in a
region with real x-y coupling.

Xsuite's `line.twiss4d()`/`twiss6d()` reports something different by default.
Its `betx`/`bety`/`alfx`/`alfy` fields are the **mode-1**/**mode-2**
(Courant-Snyder eigenmode) components only — one mode's own contribution, not
the physical projected total. The cross-mode leakage terms are computed
separately and already sit in the same twiss table as `betx2`/`bety1`/
`alfx2`/`alfy1`, but are not added back into `betx`/`bety`/`alfx`/`alfy`.
Passing `use_full_inverse=True` does not change this — it is a different
numerical method for computing the same mode-1/mode-2 convention, not a
different convention.

For an uncoupled element (a bend, a quad with no skew content, and so on) the
leakage terms are ~0 and this distinction doesn't matter — Xsuite's `betx`
and SAD's `betx` are the same thing. For a genuinely coupled element, they
are not. A solenoid is the clearest case in this codebase: confirmed on a 1m
solenoid at `BZ=1.5` (`Ks·L≈0.45`), a naive `betx` comparison against SAD is
off by **~5%**, while summing the mode components agrees with SAD to
floating-point precision:

```python
tw_sad = twiss_sad(...)
tw_xs  = line.twiss4d(betx=1.0, bety=1.0, ...)

# naive — wrong for a coupled element like a solenoid
betx_naive = tw_xs["betx", "end"]                             # 1.837438237
# projected — matches SAD's convention
betx_projected = tw_xs["betx", "end"] + tw_xs["betx2", "end"]  # 1.933552757
bety_projected = tw_xs["bety1", "end"] + tw_xs["bety", "end"]
alfx_projected = tw_xs["alfx", "end"] + tw_xs["alfx2", "end"]
alfy_projected = tw_xs["alfy1", "end"] + tw_xs["alfy", "end"]

sad_betx = tw_sad["betx"][-1]                                  # 1.933552757
```

**To compare Xsuite optics against SAD's `betx`/`bety`/`alfx`/`alfy` through a
coupled region, sum the mode components as shown above, not the raw fields.**
This is now what `tests/conversion/elements/test_sol.py`'s
`_sol_xsuite_optics_values()` does for its solenoid optics comparison.

This was originally misdiagnosed as a SAD solenoid GEO-exit-transform
reference-frame issue. It isn't: the mismatch is present already inside the
solenoid body itself (before any reference-frame transform is applied), it
scales cleanly as `(Ks·L)²`, and an independent from-scratch derivation of
the exact solenoid transfer matrix (linearizing Xsuite's own documented
solenoid Hamiltonian, cross-checked against a central-difference Jacobian
built directly from Xsuite's own tracking) matches SAD's projected `betx`
exactly — confirming both codes' underlying physics (Hamiltonian and
tracking) agree, and the gap is purely this beta-function reporting
convention.

## Additional SAD commands

Several helpers accept `additional_commands`.

This argument is inserted into the generated SAD command after the lattice is loaded and the line is selected. It can be used for local optics changes, rematching commands, or other SAD-side setup before the calculation is run.

Use this argument carefully. It is raw SAD command text and is not validated by SAD2XS.

## Timeout handling

Most helpers use `subprocess.run(..., timeout=wall_time, check=True)`.

Current behaviour:

- if SAD exceeds `wall_time`, Python raises `subprocess.TimeoutExpired`;
- if SAD exits with a non-zero status, Python raises `subprocess.CalledProcessError`;
- stdout and stderr are printed for non-zero exits where available;
- known temporary command files are removed in the handled timeout and error paths for most helpers.

`track_sad` uses `subprocess.Popen` so that progress can be read while SAD is running. It checks elapsed wall time while reading SAD output, kills the process on timeout, and raises `TimeoutError`. This timeout approach is less robust if SAD stops producing output while still running.

Default wall times are currently short for optics-style helpers and longer for tracking:

- most optics helpers default to `wall_time=30` seconds;
- `chromaticity_sad` defaults to `wall_time=60` seconds;
- `track_sad` defaults to `wall_time=24*60*60` seconds.

## Temporary files

All helpers write UUID-named temporary files directly in the current working directory (e.g. `_sad_chrom_<uid>.sad`) and remove them in a `finally` block. Concurrent calls from the same working directory are safe, and files are cleaned up on both normal and error exits.

`rebuild_sad_lattice` also writes a user-specified output lattice file; that file is intentionally persistent and is not cleaned up automatically.

Note: SAD resolves paths relative to the directory of the input script file, so temporary script files must be written to the same directory as the lattice file (i.e. the Python process cwd).

## Current safeguards

The helper layer currently provides these safeguards:

- `wall_time` limits for external SAD calls;
- `check=True` for most subprocess calls, so non-zero SAD exits are treated as failures;
- UUID-named temporary files with guaranteed cleanup via `finally` on all exit paths;
- array shape and size assertions in `track_sad`;
- explicit validation that `transfer_matrix_sad` receives either both `start_element` and `end_element`, or neither.

## Current limitations

Known limitations:

- `additional_commands` is raw SAD text and is not sandboxed or validated;
- subprocess output parsing is tailored to the current generated SAD commands;
- some error messages still use generic wording from earlier Twiss-only implementations.
