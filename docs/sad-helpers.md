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

## Twiss conventions in coupled regions (skew quads, solenoids, ...)

SAD's `twiss_sad` output (`betx`/`bety`/`alfx`/`alfy`) reports coupled optics
in the **Edwards-Teng** (decoupled normal-mode) parametrisation — the same
convention MAD-X uses — propagated from the line start. Its `R1`–`R4`
columns are the Edwards-Teng decoupling matrix, normalised as
`R / sqrt(1 + det R)`.

Xsuite's `line.twiss4d()`/`twiss6d()` reports something different by default.
Its `betx`/`bety`/`alfx`/`alfy` fields are the **mode-1**/**mode-2**
(Mais-Ripken eigenmode) components only, with the cross-mode leakage terms
in separate `betx2`/`bety1`/`alfx2`/`alfy1` columns. Xsuite can compute
Edwards-Teng parameters natively (`coupling_edw_teng=True`), but only for
periodic lines. For repository tests, `tests/support/coupled_optics.py` wraps
Xtrack's open-line Edwards-Teng propagation so converted transfer lines can be
compared against SAD through coupled regions:

```python
from tests.support.coupled_optics import edwards_teng_optics_at

tw_sad = twiss_sad(...)
tw_xs  = line.twiss4d(betx=1.0, bety=1.0, ...)

# naive — wrong for any coupled element
betx_naive = tw_xs["betx", "end"]

# Edwards-Teng — matches SAD's convention for coupled beta/alpha
et = edwards_teng_optics_at(tw_xs, "end")
betx_et = et["betx"]
```

The convention map, established empirically (each case anchored by SAD and
Xsuite 4×4 transfer-matrix equality at the 1e-10 level, so the twiss
residuals below are purely parametrisation):

| case | Edwards-Teng | Mais-Ripken projected sums (`betx1+betx2`, ...) | plain mode values |
|------|--------------|--------------------------------------------------|-------------------|
| skew-quad line | matches SAD (≤1e-9) | off by ~3e-5 (beta), ~2e-4 (alfa) | off by ~2e-5 |
| solenoid line (`BZ=1.5`) | matches SAD (≤5e-10) | identical to Edwards-Teng (≤2e-15) | off by ~5% |
| uncoupled line | matches SAD (≤1e-9) | identical to Edwards-Teng | identical to Edwards-Teng |

Two traps this map removes:

- **The projected sums are not SAD's convention**, even though they match
  it exactly for solenoids. Rotational (solenoid) coupling is a special
  case in which the Mais-Ripken projected sums numerically coincide with
  the Edwards-Teng values; for skew-quad coupling they disagree with SAD
  by more than the plain values do. An earlier version of this section
  recommended the projected sums based on the solenoid evidence alone.
- **SAD's `R1`–`R4` are not the raw decoupling matrix**: they carry the
  `1/sqrt(1 + det R)` normalisation (verified to ~1e-9 on both skew-quad
  and solenoid cases via `coupled_optics.normalized_r_matrix()`).

These facts are locked in, agreement and disagreement both asserted, by
`tests/conversion/test_coupled_twiss_convention.py`.

The solenoid mismatch was originally misdiagnosed as a SAD solenoid
GEO-exit-transform reference-frame issue. It isn't: the mismatch is present
already inside the solenoid body itself (before any reference-frame
transform is applied), it scales cleanly as `(Ks·L)²`, and an independent
from-scratch derivation of the exact solenoid transfer matrix (linearizing
Xsuite's own documented solenoid Hamiltonian, cross-checked against a
central-difference Jacobian built directly from Xsuite's own tracking)
matches SAD's reported `betx` exactly — confirming both codes' underlying
physics (Hamiltonian and tracking) agree, and the gap is purely this
reporting convention.

## Additional SAD commands

Several helpers accept `additional_commands`.

This argument is inserted into the generated SAD command after the lattice is loaded and the line is selected. It can be used for local optics changes, rematching commands, or other SAD-side setup before the calculation is run.

Use this argument carefully. It is raw SAD command text and is not validated by SAD2XS.

## Output and error handling

Helpers are silent by default. Progress messages and SAD's own terminal output are emitted through the `sad2xs` logger: `sad2xs.set_log_level("debug")` exposes them. There are no per-function verbosity parameters; the tqdm progress bar in `track_sad` remains controlled by `with_progress`.

Most helpers run SAD through a shared runner (`run_sad` in `sad_helpers/_helpers.py`) which uses `subprocess.run(..., timeout=wall_time, check=True)`.

Current behaviour:

- if SAD exceeds `wall_time`, a `RuntimeError` naming the helper and the wall time is raised;
- if SAD exits with a non-zero status, a `RuntimeError` is raised with SAD's stdout and stderr embedded in the message, so the diagnostic travels with the exception;
- the original `subprocess` exception is preserved as the `__cause__` of the `RuntimeError`;
- on success, SAD's terminal output is logged at debug level;
- the temporary command file is removed on all exit paths.

`track_sad` uses `subprocess.Popen` so that progress can be read while SAD is running. It checks elapsed wall time while reading SAD output, kills the process on timeout, and raises `RuntimeError` with the same conventions (SAD's output embedded on failure). This timeout approach is less robust if SAD stops producing output while still running.

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
- subprocess output parsing is tailored to the current generated SAD commands.
