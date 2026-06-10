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
- `003_fccee_sol.py`: rebuild, convert, and compare a public solenoid lattice.
- `004_fccee_sol_e-e+.py`: compare positron and electron-ring solenoid conversions.
- `_example_helpers.py`: runtime setup, plotting, and comparison helpers shared by the examples.
- `lattices/`: public SAD lattice inputs used by the examples.

## Notes

These scripts call SAD through `sad2xs.sad_helpers`, generate plots, and may take longer than unit tests. Public regression tests should live under `tests/` and should use reduced synthetic inputs where possible.
