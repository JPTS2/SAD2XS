# Contributing

This document records the development workflow used for the current release cycle.

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

Use the issue number when one exists. Keep names descriptive enough that the branch purpose is clear in GitHub and local tooling.

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

Before publishing a package release, update all package version metadata to the released version. At minimum, check `setup.py`; if future packaging files are added, such as `pyproject.toml` or a dedicated version module, they must be updated consistently as part of the release branch before tagging.

## Commit style

Commit messages should be short and specific.

Examples:

```text
Fix verbose flag changing aperture conversion
Add parser regression tests for comma-separated lines
Document Xsuite model as canonical conversion layer
```

## Environment

Use the `xsuite` conda environment for Python commands:

```bash
conda run -n xsuite pytest
conda run -n xsuite python -m pytest tests/test_001_drift.py
```

For documentation-only changes, Python tests are not normally required unless examples or generated outputs are changed.

GitHub CLI commands can also be run from the same environment when needed:

```bash
conda run -n xsuite gh issue list
```

## Public issue policy

Issues should describe shareable behaviour.

If a private lattice exposes a bug, the public issue should describe the minimal public reproduction or the general converter feature that is missing. Do not include private lattice files, private names, or machine-specific details that are not shareable.
