# Installation Tests

This folder contains tests for installer and installation helper behaviour.

Use these tests for command construction, executable discovery, platform
installation policy, and minimal SAD executable smoke checks. Do not run
destructive installation steps from tests.

Installation-specific input files, such as `sad_installation_test.sad`, live
beside these tests. Introduce a shared fixture folder only if fixture data is
reused across unrelated test areas.

## Coverage

Requires the SAD binary for the executable smoke test.

| File | Tests | Fail | Failure root cause |
|------|-------|------|--------------------|
| `test_macos_installer.py` | 13 | 0 | — |
| `test_sad_executable.py` | 1 | 0 | — |

- `test_macos_installer.py` — macOS installer internals via
  monkeypatching: `_run` error handling and non-zero return codes, brew cask
  flag, brew prefix with missing formula, executable name resolution,
  `ensure_command_exists` skip and install paths, X11 header detection,
  dependency installation order, conda environment variable stripping and
  toolchain setup, launcher file writing, shell RC deduplication and creation.

- `test_sad_executable.py` — SAD executable smoke check: verifies the
  `sad` command is on PATH and runs the committed installation test lattice
  (`sad_installation_test.sad`) to completion with returncode 0.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
