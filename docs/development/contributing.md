# Contributing

This document records the development workflow used for the current release cycle.

**On this page:**

- [Branch model](#branch-model)
- [Pull requests](#pull-requests)
- [Releases and tags](#releases-and-tags)
- [Commit style](#commit-style)
- [Environment](#environment)
- [Terminal output policy](#terminal-output-policy)
- [Public issue policy](#public-issue-policy)

## Branch model

`main` is the stable branch.

`release/x.y.z` is the integration branch for the next planned release, where `x.y.z` is the version being prepared.

Issue branches should be created from the active release branch and should normally be merged back into that release branch by pull request.

For example, while preparing version `0.3.0`, the active release branch would be `release/0.3.0`.

Recommended branch naming:

```text
docs/24-architecture-and-conversion-model
test/20-public-test-baseline
fix/26-verbose-logging-only
feature/30-comma-separated-lines
```

Use the tracker ID when one exists. Keep names descriptive enough that the branch purpose is clear in GitHub and local tooling.

Before starting work, make sure the working tree is clean and the issue branch is based on the active release branch.

## Pull requests

Pull requests should:

- target the active release branch during the current release cycle;
- link the relevant issue;
- keep changes scoped to one issue where practical;
- include tests for behaviour changes;
- update documentation when behaviour, architecture, or workflow changes;
- avoid unrelated formatting churn;
- avoid public references to private or non-shareable lattices.

If a change is discovered to be larger than expected, split it into smaller pull requests before review becomes difficult.

## Releases and tags

GitHub releases and version tags should be used for actual published versions, not for temporary development branches.

Do not tag issue branches or intermediate cleanup states. When the active release branch is complete, it should be merged to `main`, tagged as the released version, and published as a GitHub release.

Before publishing a package release, update all package version metadata to the released version. The version is carried in `pyproject.toml` and `CITATION.cff`. Update both consistently as part of the release branch, before tagging.

[Releasing](releasing.md) gives the full step-by-step procedure, including the package build checks and the Zenodo archive.

## Commit style

Commit messages should be short and specific.

Examples:

```text
Fix verbose flag changing aperture conversion
Add parser regression tests for comma-separated lines
Document Xsuite model as canonical conversion layer
```

## Environment

Install the development dependencies from a checkout:

```bash
pip install -e ".[dev]"
```

The `dev` extra pulls in `sad-helpers`, `plotting`, and `test`, which together cover everything the test suite imports.

`environment.yml` builds the same set through conda, if a conda environment is preferred:

```bash
micromamba env create -f environment.yml
```

Both files declare the same packages. `tests/packaging/test_environment_matches_pyproject.py` fails if they drift apart, so a dependency added to one must be added to the other.

```bash
pytest
```

For documentation-only changes, Python tests are not normally required unless examples or generated outputs are changed.

GitHub CLI commands can be run from any shell where `gh` is available:

```bash
gh issue list
```

## Terminal output policy

All package terminal output goes through the `sad2xs` logger hierarchy. Never call `print()` in `sad2xs/`. A source-scan test, `tests/observability/test_no_print_statements.py`, fails on any print call. Get a logger at module level with `logger = logging.getLogger(__name__)`.

This holds for console scripts too. `initialise_logging()` runs on package import, so a `[project.scripts]` entry point already has a configured logger by the time it starts; it only has to raise the level, as `sad2xs-install-sad` does with `set_log_level("info")`. Output that a command streams from a subprocess is not package output, and is passed through unchanged.

Level semantics:

- **error**: never logged — raise an exception instead, with the diagnostic context (element names, line numbers, external SAD output) embedded in the exception message;
- **warning**: the converter changed, assumed, or dropped something relative to the source file. Always visible, even in quiet mode. Must name the element and/or source line where available;
- **info**: the progress narrative. Section headings (`log_section_heading`) plus one result line per stage stating what was done ("Converted 42 bend definitions"). Off by default;
- **debug**: per-element decisions (simplifications, absorbed rotations, redefinitions) and external SAD terminal output.

The single user-facing control is `sad2xs.set_log_level("debug" | "info" | "warning" | "error")`. `_verbose=True` on the converter is shorthand that raises the level to info. Do not add per-function verbosity parameters. The observability tests enforce their absence on the SAD helpers.

Quiet mode, which is the default, must produce **no output at all** for a warning-free conversion. This includes progress bars from dependencies. `tests/observability/test_quiet_converter_output.py` enforces this end to end. If you add a stage that can emit output on lattices the test lattice does not cover, extend the test lattice.

## Public issue policy

Issues should describe shareable behaviour.

If a private lattice exposes a bug, the public issue should describe the minimal public reproduction or the general converter feature that is missing. Do not include private lattice files, private names, or machine-specific details that are not shareable.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
