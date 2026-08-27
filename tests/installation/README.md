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
| `test_installer_dispatch.py` | 9 | 0 | — |
| `test_installer_helpers.py` | 40 | 0 | — |
| `test_macos_installer.py` | 30 | 0 | — |
| `test_real_installation.py` | 1 | 0 | — |
| `test_sad_executable.py` | 1 | 0 | — |

### `test_installer_dispatch.py`

Covers the command line and the platform choice: argument parsing into
an `InstallConfig`, the guard each platform module applies to itself, and
how the command reports a platform it cannot serve or a build that failed.

| Test | What it asserts |
|------|-----------------|
| `test_require_platform_allows_the_macos_installer_on_macos` | An installer running on the platform it supports should proceed. |
| `test_require_platform_exits_when_the_macos_installer_runs_on_linux` | An installer run directly on the wrong platform should exit, naming the command that picks the right one. |
| `test_the_command_line_defaults_to_the_xdg_locations` | With no arguments the install should land in the XDG directories. |
| `test_prefix_redirects_the_whole_install` | A single --prefix should move the source tree and the build logs. |
| `test_a_user_relative_prefix_is_expanded` | A ~ in a path should be expanded rather than taken literally. |
| `test_install_sad_exits_when_no_installer_exists_for_the_platform` | A platform with no installer should exit, naming those that have one. |
| `test_install_sad_hands_the_parsed_config_to_the_macos_installer` | On macOS the command should reach the macOS installer, with the config. |
| `test_install_sad_reports_a_failed_build_without_a_traceback` | A failed build step should exit with its message, not a stack trace. |
| `test_a_named_branch_is_marked_as_explicitly_requested` | A branch given on the command line should be distinguishable. |

### `test_installer_helpers.py`

Covers the platform-independent installer machinery in `_helpers.py` by
monkeypatching subprocess calls. No test clones, builds, or writes outside
`tmp_path`. Weighted towards the destructive paths: which source trees may
be replaced, what happens when a clone or a source request fails, and what
reaches the launcher and the printed PATH instruction.

| Test | What it asserts |
|------|-----------------|
| `test_install_config_derives_prefix_paths` | Every build path should follow from the prefix alone. |
| `test_install_config_puts_the_launcher_in_the_bin_directory` | The launcher follows bin_dir, not the prefix, so the two move apart. |
| `test_install_config_makes_a_relative_prefix_absolute` | A relative --prefix must not reach the launcher script. |
| `test_run_raises_command_error_on_nonzero_return_code` | run should raise CommandError when a checked command returns non-zero. |
| `test_run_check_false_returns_completed_process_on_nonzero` | run should return the CompletedProcess when check=False. |
| `test_run_raises_with_the_log_path_when_a_logged_command_fails` | A failed build step should carry the log that explains it. |
| `test_run_survives_build_output_that_is_not_valid_utf8` | A compiler in a non-UTF-8 locale should not kill the build. |
| `test_log_tail_reports_the_end_of_a_long_log` | A build failure should surface the end of the log, where the cause is. |
| `test_log_tail_reports_a_missing_log_without_raising` | A log that was never created must not mask the build failure itself. |
| `test_clone_sad_refuses_to_delete_a_source_tree_it_does_not_own` | An unrelated <prefix>/src must never be removed. |
| `test_a_marker_beside_the_source_tree_does_not_authorise_deleting_it` | Ownership must be proved by the tree itself, not by its parent. |
| `test_clone_sad_replaces_a_tree_it_marked_as_its_own` | The marker inside a source tree identifies it as safe to replace. |
| `test_a_failed_clone_leaves_the_previous_source_tree_untouched` | A clone that fails must not cost the user a working installation. |
| `test_a_failed_clone_leaves_no_ownership_marker` | A half-finished install must not claim ownership of anything. |
| `test_an_absent_explicit_branch_leaves_the_previous_source_tree_untouched` | A typo in --branch must be reported before anything is deleted. |
| `test_guard_prefix_catches_a_home_directory_reached_through_a_symlink` | A symlinked home must still be refused as an install prefix. |
| `test_clone_sad_fails_when_an_explicitly_named_branch_is_absent` | A mistyped --branch should stop the install, not install other source. |
| `test_clone_sad_falls_back_to_the_remote_default_branch` | The default branch name only should tolerate an upstream rename. |
| `test_clone_sad_reports_a_remote_failure_as_a_remote_failure` | A network or repository failure is not an absent branch. |
| `test_clone_sad_reports_a_git_that_cannot_be_run` | A missing git should say so rather than surface as a traceback. |
| `test_clone_sad_refuses_to_reuse_a_checkout_whose_origin_is_not_the_request` | Reuse validation fails closed on anything that is not a match. |
| `test_clone_sad_refuses_to_reuse_a_checkout_with_no_usable_branch` | An unreadable or detached HEAD cannot satisfy an explicit --branch. |
| `test_clone_sad_keeps_a_matching_tree_and_reports_the_reuse` | A matching checkout should be kept, and the reuse reported. |
| `test_clone_sad_reports_no_reuse_when_asked_to_reuse_a_tree_that_is_absent` | --reuse-clone with nothing to reuse is still a fresh clone. |
| `test_clone_sad_truncates_the_build_log_even_when_reusing_a_tree` | A reused tree must still start from an empty build log. |
| `test_make_sad_cleans_only_a_reused_tree` | A fresh clone has nothing to clean, and upstream's clean target fails when there is nothing to remove. |
| `test_verify_executable_accepts_an_executable_binary` | A build that produced a runnable binary should pass without exiting. |
| `test_verify_executable_rejects_a_binary_without_the_executable_bit` | A file that exists but cannot be run is a failed build. |
| `test_verify_executable_exits_when_the_build_produced_no_binary` | A build that returns zero but leaves no binary should still fail. |
| `test_write_launcher_writes_an_executable_script` | write_launcher should create an executable script pointing at the build. |
| `test_write_launcher_quotes_a_prefix_containing_shell_metacharacters` | An awkward prefix should reach the launcher as a literal path. |
| `test_report_path_setup_is_quiet_when_the_directory_is_on_path` | A launcher directory already on PATH needs nothing from the user. |
| `test_report_path_setup_prints_the_export_without_touching_any_rc_file` | An unreachable launcher directory should be reported, never wired up. |
| `test_report_path_setup_prints_an_export_a_shell_can_run` | The printed line is meant to be pasted, so it must run as printed. |

### `test_macos_installer.py`

Covers the macOS-specific parts: read-only dependency probes, the missing-
dependency report, the sanitised build PATH, the Xcode toolchain
environment, and the order of the full installation sequence. Every
subprocess call is monkeypatched.

Two contracts are held directly here. The installer never installs a system
dependency, asserted over the module source and over every subprocess call
it constructs. Build-time commands are probed on exactly the PATH the build
receives, so a command supplied only by conda is reported missing rather
than disappearing once the build starts.

| Test | What it asserts |
|------|-----------------|
| `test_brew_prefix_returns_none_when_the_formula_is_absent` | A failed prefix lookup should report absence, never install anything. |
| `test_brew_prefix_returns_none_when_homebrew_cannot_be_run` | An absent brew executable should report absence, not raise. |
| `test_check_xcode_clt_passes_when_the_tools_are_configured` | A configured toolchain should report nothing missing. |
| `test_check_xcode_clt_reports_the_command_that_installs_them` | Unconfigured Command Line Tools should be reported naming the fix. |
| `test_build_path_puts_homebrew_ahead_of_the_system_directories` | The build PATH should be Homebrew then macOS, and nothing else. |
| `test_build_path_falls_back_to_the_system_directories_without_homebrew` | An absent Homebrew should leave only the macOS system directories. |
| `test_the_audit_and_the_build_use_the_same_path` | The PATH the audit probes must be the PATH the build receives. |
| `test_check_command_passes_when_the_command_is_on_path` | A command already on PATH should report nothing missing. |
| `test_check_command_reports_the_remedy_for_a_missing_command` | A missing command should be reported with its manual command. |
| `test_check_command_searches_only_the_path_it_is_given` | An explicit PATH should be searched instead of the caller's. |
| `test_a_build_command_supplied_only_by_conda_is_reported_missing` | A command that only conda supplies must not pass the build audit. |
| `test_a_build_command_on_the_sanitised_path_is_accepted` | A command the sanitised PATH supplies should pass the build audit. |
| `test_git_is_probed_on_the_callers_path` | git should be found the way the clone will find it. |
| `test_check_brew_bin_passes_when_the_formula_provides_it` | A present, runnable formula executable should report nothing missing. |
| `test_check_brew_bin_reports_an_executable_that_cannot_be_run` | A present but non-executable file should be reported missing. |
| `test_check_brew_bin_reports_a_formula_that_is_not_installed` | A prefix for an uninstalled formula should still report it missing. |
| `test_check_brew_bin_reports_an_absent_formula` | A formula with no prefix should be reported, not installed. |
| `test_check_x11_headers_reports_the_cask_when_headers_are_missing` | Missing X11 headers should be reported, never installed. |
| `test_check_x11_headers_passes_when_the_header_is_present` | Present X11 headers should report nothing missing. |
| `test_audit_dependencies_reports_nothing_when_everything_is_present` | A complete dependency set should produce an empty report. |
| `test_audit_dependencies_reports_homebrew_without_probing_its_formulae` | An absent Homebrew should be reported without a formula probe. |
| `test_audit_dependencies_reports_every_miss_together` | Several missing dependencies should be reported in one pass. |
| `test_require_dependencies_returns_when_nothing_is_missing` | A complete dependency set should let the install proceed. |
| `test_require_dependencies_exits_listing_every_manual_command` | Missing dependencies should exit non-zero naming each manual command. |
| `test_install_sad_macos_stops_before_cloning_when_dependencies_are_missing` | A missing dependency should stop the install before SAD is fetched. |
| `test_the_macos_installer_has_no_package_installation_path` | No installer source line may name a package-manager install command. |
| `test_the_macos_installer_never_runs_an_install_subcommand` | No subprocess the installer launches may carry an install subcommand. |
| `test_make_clean_build_env_exits_when_a_tool_path_does_not_exist` | A toolchain variable pointing nowhere should fail before the build. |
| `test_make_clean_build_env_exits_when_homebrew_has_no_prefix` | An unusable Homebrew should fail naming the prefix, not crash later. |
| `test_install_sad_macos_runs_every_stage_in_order` | The install should check dependencies, fetch, build, verify, then link. |

### `test_real_installation.py`

Opt-in end-to-end install. Clones and builds SAD into a temporary prefix,
then runs the smoke lattice through the generated launcher. Needs the
network and takes minutes, so it is skipped unless
`SAD2XS_REAL_INSTALL_TEST=1` is set.

| Test | What it asserts |
|------|-----------------|
| `test_installer_builds_sad_and_the_launcher_runs_the_smoke_lattice` | A real install should produce a launcher that runs a SAD lattice. |

### `test_sad_executable.py`

Smoke check against a real SAD installation. Requires the SAD binary.

| Test | What it asserts |
|------|-----------------|
| `test_sad_executable_runs_installation_smoke_lattice` | The installed SAD executable should run the committed installation smoke lattice without returning an error. |

## Real Installation Validation

Every other test in this folder monkeypatches its subprocess calls, so none of
them proves the installer can actually build SAD. `test_real_installation.py`
does, but it needs the network and takes minutes, so it does not run by
default.

To run it:

```bash
SAD2XS_REAL_INSTALL_TEST=1 python -m pytest tests/installation/test_real_installation.py -v
```

It installs into a pytest `tmp_path`, never the default location, and asserts
that `~/.zshrc` and `~/.bashrc` are byte-identical afterwards.

Last run: 2026-08-29, macOS 15 (Darwin 25.5.0), arm64, from an active conda
environment. Passed in 197 s: clone into a staging directory, swap into place,
`make depend`, `make exe`, a runnable `src/bin/gs`, and the smoke lattice
completing with return code 0 through the generated launcher invoked from an
unrelated working directory. Both shell rc files were unchanged, checked for
modification and for creation.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
