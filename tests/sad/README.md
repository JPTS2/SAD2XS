# SAD Syntax Assumption Tests

This folder contains empirical tests that verify which parameters each SAD element
type accepts or rejects at runtime. They serve as the machine-verified specification
that the SAD2XS converter mirrors.

## Motivation

The converter must only parse parameters that SAD itself recognises for each element
type. Building converter paths for parameters SAD silently discards would create
unreachable code and untestable branches. These tests pin the boundary so the
converter stays honest.

The findings are consistent with confirmation from K. Oide (SAD author, 2026-06-24):

> *"QUAD, SEXT, OCT, DECA only take their specific component K1, K2, K3, K4,
> respectively. Similarly, BEND takes ANGLE and K0. So anything beyond that must
> be declared as MULT, which is an almighty, even an acceleration can be included.
> These are mostly by a historical reason."*

## Test harness

Each test builds a minimal lattice file (one element between START/END markers),
then calls `twiss_sad` from `sad2xs.sad_helpers` with `closed=False, calc6d=False`
— a 4D transfer-line Twiss. The test `os.chdir`s to `tmp_path` and passes a
relative filename; SAD's shell wrapper requires a relative path in the working
directory. If SAD exits non-zero the parameter is **rejected**; if it exits zero
it is **accepted**.

## Coverage

187 tests across 12 files. All require the SAD binary.

### Parameter matrix

| Element | Accepted | Rejected |
|---------|----------|---------|
| QUAD | K1, DX, DY, ROTATE | ANGLE, K0, SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ |
| SEXT | K2, DX, DY, ROTATE | ANGLE, K0, SK0, K1, SK1, SK2, K3–K4, SK3–SK4, HARM, FREQ, BZ |
| OCT | K3, DX, DY, ROTATE | ANGLE, K0, SK0, K1–K2, SK1–SK2, SK3, K4, SK4, HARM, FREQ, BZ |
| BEND | ANGLE, K0, K1, DX, DY, ROTATE | SK0, SK1, K2–K4, SK2–SK4, HARM, FREQ, BZ |
| MULT | ANGLE, K0–K4, SK0–SK4, DX, DY, ROTATE, HARM, FREQ | BZ |
| CAVI | VOLT, FREQ, HARM, PHI, DX, DY, ROTATE | ANGLE, K0–K4, SK0–SK4, BZ |
| SOL | BZ, DX, DY | ANGLE, K0–K4, SK0–SK4, HARM, FREQ, ROTATE |
| DRIFT | bare only (L) | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ, DX, DY, ROTATE |
| APERT | AX, AY, DX, DY, ROTATE | ANGLE, K0–K4, SK0–SK4, BZ, HARM, FREQ |
| MARK | bare, BZ, DX, DY | K1–K3, ROTATE, FREQ |
| MONI | bare, DX, DY, ROTATE | K0–K2, BZ, ANGLE, FREQ, HARM |

### SOL structural requirement

SOL is a zero-length fringe element. The physical length lives in a DRIFT between
an entrance SOL and an exit SOL. `BOUND=1` is required on the entrance and exit
elements; inner SOL elements (if any) do not require it. `GEO=1` marks the
field-centre element of each solenoid body.

Minimum valid pattern: `SOL(BZ, BOUND=1, GEO=1) + DRIFT + SOL(BZ=0, BOUND=1)`

`test_sol.py` probes single-element, pair-without-drift, pair-without-GEO, and
pair-without-BOUND configurations before running the parameter accept/reject tests.
It also verifies that an inner SOL without BOUND is valid in a three-element chain.

A degenerate SOL pair with BOUND on both elements but no GEO (`test_sol_pair_no_geo_rejects`)
is not rejected by SAD's exit code — SAD exits 0 but writes Mathematica undefined symbols
(e.g. `medium`, `$DefaultFontWeight`) into the TFS output, indicating the Twiss computation
failed silently. `twiss_sad` detects these symbols and raises `ValueError`, which `sad_rejects`
treats as a rejection.

### LINE definitions

`test_line.py` verifies SAD's LINE syntax rather than element parameter acceptance:

| Test | Verifies |
|------|----------|
| `test_line_name_containing_line_substring_is_accepted` | Line names containing the substring `line` (e.g. `MYLINE`) are valid identifiers — SAD does not treat the substring as the keyword |
| `test_nested_line_reference_containing_line_substring_is_accepted` | Such names are also valid when referenced nested inside another LINE definition |
| `test_line_keyword_with_newline_before_name_is_accepted` | A newline between the `LINE` keyword and the line name/definition is accepted by SAD |

## Elements not tested and why

**BEAMBEAM** — Beam–beam elements are not currently converted by SAD2XS. Testing
their SAD parameter acceptance is premature and out of scope.
