# Examples

This folder contains public SAD2XS example scripts and public SAD lattice inputs.

These examples are intended for manual validation and demonstration. They are not part of the pytest test suite.

## Requirements

The examples require:

- a Python environment with SAD2XS and its dependencies installed;
- a working SAD executable available as `sad`, or an equivalent executable configured in the scripts;
- the Python dependencies used by SAD2XS and the plotting helpers.

## Running an example

Run examples from the repository root or from this folder:

```bash
python examples/001_fccee_zh.py
```

Each script resolves its own location and uses paths relative to this `examples/` folder. Generated SAD2XS output files are written to `examples/out/`, which is ignored by Git.

Some examples also create a temporary rebuilt SAD lattice under `examples/lattices/`. Files matching `*_rebuilt.sad` are ignored by Git.

## Contents

- `001_fccee_zh.py`: convert and compare a public ZH lattice.
- `002_fccee_tt_collimation.py`: convert and compare a public tt collimation lattice.
- `003_fccee_coupled.py`: convert and compare a public coupled lattice; demonstrates
  that SAD's coupling matrix (R1-R4) and coupled beta functions require
  Edwards-Teng columns to compare against SAD, not Xsuite's plain
  Mais-Ripken-mode columns.
- `004_fccee_sol.py`: rebuild, convert, and compare a public solenoid lattice.
- `005_fccee_sol_e-e+.py`: compare positron and electron-ring solenoid conversions.
- `_runtime.py`: runtime setup (working directory, output folder) shared by the examples. Plotting and comparison helpers live in `sad2xs.xsuite_helpers`, not a local file.
- `lattices/`: public SAD lattice inputs used by the examples.

## Notes

These scripts call SAD through `sad2xs.sad_helpers`, generate plots, and may take longer than unit tests. Public regression tests should live under `tests/` and should use reduced synthetic inputs where possible.
