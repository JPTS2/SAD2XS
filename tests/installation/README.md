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
| `test_installer_dispatch.py` | 11 | 0 | — |
| `test_installer_helpers.py` | 90 | 0 | — |
| `test_linux_installer.py` | 52 | 0 | — |
| `test_macos_installer.py` | 32 | 0 | — |
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

The install is one transaction: source, build, and launcher together. An
unowned launcher is refused before anything is cloned or moved, any previous
source tree is held aside for the whole clone, preparation, build, and
launcher write, and it is put back if any of them fails. A first install has
no backup to restore, so rollback removes the tree it created instead.

Recovery does not depend on catching an exception. The transaction lives at a
fixed `.sad2xs-transaction` directory carrying its own versioned record, so a
run killed outright is discoverable, the next invocation reconciles it before
starting, and a directory that merely shares the name is never mistaken for
one of ours. The record's `had_previous` is what separates "the clone never
finished" from "a first install reached `src`" — both have no backup.
The same validated state drives startup recovery and in-process rollback.
Ownership files must be regular files, without following symlinks. Anything
malformed, unmarked, or contradictory is named and left alone.

The commit is an atomic rename of the transaction to a distinct cleanup path.
Clearing that up afterwards may fail and only warns, and a later run never
reads it as rollback state.

The clone lands in the transaction and is renamed to `src` before the build,
because SAD bakes its build directory into the binary as an rpath and in the
Tcl/Tk library paths. Building elsewhere and renaming afterwards produces a
binary that cannot find its libraries. That was found by the real-install
test, not by the monkeypatched ones.

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
| `test_prepare_source_refuses_to_delete_a_source_tree_it_does_not_own` | An unrelated <prefix>/src must never be removed. |
| `test_a_marker_beside_the_source_tree_does_not_authorise_deleting_it` | Ownership must be proved by the tree itself, not by its parent. |
| `test_a_symlinked_source_marker_does_not_authorise_deleting_the_tree` | Ownership must come from a regular marker inside the source tree. |
| `test_prepare_source_holds_the_previous_tree_aside_rather_than_deleting_it` | A replacement clone must keep the previous tree recoverable. |
| `test_prepare_source_restores_the_previous_tree_when_the_clone_fails` | A failed clone should put the previous tree straight back. |
| `test_a_failed_clone_leaves_the_previous_source_tree_untouched` | A clone that fails must not cost the user a working installation. |
| `test_a_failed_clone_leaves_no_ownership_marker` | A half-finished install must not claim ownership of anything. |
| `test_an_absent_explicit_branch_leaves_the_previous_source_tree_untouched` | A typo in --branch must be reported before anything is deleted. |
| `test_guard_prefix_catches_a_home_directory_reached_through_a_symlink` | A symlinked home must still be refused as an install prefix. |
| `test_prepare_source_fails_when_an_explicitly_named_branch_is_absent` | A mistyped --branch should stop the install, not install other source. |
| `test_prepare_source_falls_back_to_the_remote_default_branch` | The default branch name only should tolerate an upstream rename. |
| `test_prepare_source_reports_a_remote_failure_as_a_remote_failure` | A network or repository failure is not an absent branch. |
| `test_prepare_source_reports_a_git_that_cannot_be_run` | A missing git should say so rather than surface as a traceback. |
| `test_prepare_source_refuses_to_reuse_a_checkout_whose_origin_is_not_the_request` | Reuse validation fails closed on anything that is not a match. |
| `test_prepare_source_refuses_to_reuse_a_checkout_with_no_usable_branch` | An unreadable or detached HEAD cannot satisfy an explicit --branch. |
| `test_prepare_source_keeps_a_matching_tree_and_reports_the_reuse` | A matching checkout should be kept, and the reuse reported. |
| `test_prepare_source_reports_no_reuse_when_asked_to_reuse_a_tree_that_is_absent` | --reuse-clone with nothing to reuse is still a fresh clone. |
| `test_prepare_source_truncates_the_build_log_even_when_reusing_a_tree` | A reused tree must still start from an empty build log. |
| `test_make_sad_cleans_only_a_reused_tree` | A fresh clone has nothing to clean, and upstream's clean target fails when there is nothing to remove. |
| `test_verify_executable_accepts_an_executable_binary` | A build that produced a runnable binary should pass without exiting. |
| `test_verify_executable_rejects_a_binary_without_the_executable_bit` | A file that exists but cannot be run is a failed build. |
| `test_verify_executable_exits_when_the_build_produced_no_binary` | A build that returns zero but leaves no binary should still fail. |
| `test_a_failure_at_any_stage_leaves_the_previous_installation_working` | An install that fails must cost the user nothing. |
| `test_a_verified_install_replaces_the_previous_one_and_leaves_no_state` | A build that passes verification should become the installation. |
| `test_an_unowned_launcher_is_refused_before_anything_is_cloned_or_moved` | An unowned launcher should cost no clone, no build, and no move. |
| `test_an_interrupted_install_is_recovered_by_the_next_invocation` | A run killed outright must not hide the working installation. |
| `test_startup_recovery_reports_filesystem_failures_with_every_state_path` | Recovery I/O failures should be actionable without exposing a traceback. |
| `test_an_interruption_during_the_clone_leaves_the_source_untouched` | A run killed during the clone has nothing to restore. |
| `test_a_fresh_invocation_recovers_an_interrupted_install` | The next run of the installer should reconcile before doing anything. |
| `test_a_first_install_that_fails_leaves_nothing_behind` | A failed first install must not leave a broken tree pretending to work. |
| `test_a_first_install_killed_after_activation_is_recovered` | A first install killed after its tree reached src must not look done. |
| `test_a_first_install_leaves_an_unmarked_tree_alone` | Recovery must not delete a tree at src it cannot prove it created. |
| `test_an_unmarked_transaction_directory_is_refused_and_preserved` | A directory that merely shares the name is not this installer's. |
| `test_a_malformed_transaction_record_is_refused` | A record this installer cannot read is not one it may act on. |
| `test_a_symlinked_transaction_record_is_refused_and_preserved` | A transaction record must be a regular file owned by the transaction. |
| `test_a_transaction_symlink_is_refused_and_its_target_untouched` | Recovery must never follow a symlink out of the prefix and delete. |
| `test_a_contradictory_transaction_is_refused_and_preserved` | Recovery must not guess when the record contradicts the filesystem. |
| `test_a_failed_commit_cleanup_does_not_roll_the_install_back` | Clearing up after a commit is tidying, not part of the transaction. |
| `test_an_interrupted_replacement_before_the_old_tree_moves` | A run killed before the old tree moved should keep it exactly there. |
| `test_recovery_refuses_state_it_cannot_identify_as_its_own` | Recovery must not delete a tree it cannot prove it created. |
| `test_rollback_preserves_transaction_state_it_cannot_validate` | In-process rollback must fail closed like startup reconciliation. |
| `test_a_rollback_that_cannot_complete_preserves_and_names_the_backup` | A rollback that fails must never lose the only working copy. |
| `test_reuse_clone_builds_in_place_without_cloning_another_tree` | --reuse-clone must rebuild the tree it was pointed at. |
| `test_write_launcher_writes_an_executable_script` | write_launcher should create an executable script pointing at the build. |
| `test_write_launcher_quotes_a_prefix_containing_shell_metacharacters` | An awkward prefix should reach the launcher as a literal path. |
| `test_report_path_setup_is_quiet_when_the_launcher_is_the_one_that_runs` | A launcher that the shell would actually run needs nothing from the user. |
| `test_write_launcher_refuses_an_unowned_regular_file` | A sad already on PATH that this installer did not write is not ours. |
| `test_write_launcher_refuses_a_file_that_merely_mentions_the_marker` | The marker has to be one of the file's own lines. |
| `test_write_launcher_refuses_a_symlink_and_leaves_its_target_alone` | A symlink must not be followed, or the write lands on its target. |
| `test_write_launcher_refuses_a_directory` | A directory at the launcher path is not something to replace. |
| `test_write_launcher_replaces_a_launcher_it_wrote_itself` | Reinstalling should upgrade the launcher this installer left behind. |
| `test_a_failed_launcher_write_leaves_no_staging_file` | An interrupted write must leave nothing behind on PATH. |
| `test_report_path_setup_warns_when_another_sad_shadows_the_launcher` | An earlier sad on PATH should be named, not silently accepted. |
| `test_report_path_setup_warns_when_the_launcher_does_not_resolve` | A launcher directory on PATH with no runnable sad should be reported. |
| `test_report_path_setup_prints_the_export_without_touching_any_rc_file` | An unreachable launcher directory should be reported, never wired up. |
| `test_report_path_setup_prints_an_export_a_shell_can_run` | The printed line is meant to be pasted, so it must run as printed. |
| `test_no_installer_module_has_a_package_installation_path` | No installer source line may name a command that installs packages. |
| `test_no_installer_module_runs_an_install_subcommand` | No subprocess any installer module launches may install packages. |

### `test_linux_installer.py`

Covers the Linux-specific parts: distribution detection, per-family package
suggestions, read-only dependency probes, the sanitised system PATH, the
conda-free build environment, the sad.conf truncation KEK's instructions
call for, and the order of the full installation sequence. Every subprocess
call is monkeypatched apart from the generated launcher, which is executed.

Build-time commands are probed on exactly the PATH the build receives, so a
command supplied only by conda is reported missing rather than disappearing
once the build starts. The non-mutating policy guard is not here: it lives
in `test_installer_helpers.py` and covers every module in the package.

| Test | What it asserts |
|------|-----------------|
| `test_distro_family_maps_a_distribution_to_its_packaging_family` | A distribution should map to the family whose package names apply. |
| `test_distro_family_is_unknown_when_os_release_cannot_be_read` | An absent os-release should give no family rather than raise. |
| `test_package_suggestion_names_the_package_for_the_family` | The same dependency should be named the way its distribution names it. |
| `test_package_suggestion_falls_back_when_the_family_is_unknown` | An unrecognised distribution should get an instruction, not a guess. |
| `test_package_suggestion_passes_through_a_name_it_has_no_mapping_for` | A dependency named the same everywhere needs no mapping. |
| `test_build_path_is_the_system_directories_alone` | The build PATH should carry the distribution's directories only. |
| `test_the_audit_and_the_build_use_the_same_path` | The PATH the audit probes must be the PATH the build receives. |
| `test_a_build_command_supplied_only_by_conda_is_reported_missing` | A command that only conda supplies must not pass the build audit. |
| `test_a_build_command_on_the_sanitised_path_is_accepted` | A command the sanitised PATH supplies should pass the build audit. |
| `test_git_is_probed_on_the_callers_path` | git should be found the way the clone will find it. |
| `test_the_audit_reports_every_miss_together` | Several missing dependencies should be reported in one pass. |
| `test_check_x11_headers_accepts_a_multiarch_header` | A header under a triplet directory should count as present. |
| `test_check_x11_headers_reports_the_package_when_absent` | Absent X11 headers should be reported with the distribution's package. |
| `test_make_clean_build_env_strips_conda_settings_and_pins_the_toolchain` | The build environment should drop conda settings and name the compilers. |
| `test_make_clean_build_env_refuses_to_use_gcc_as_the_cxx_compiler` | gcc must not stand in for g++. |
| `test_the_audit_reports_a_missing_gxx` | A machine with gcc but no g++ should be told which package supplies it. |
| `test_make_clean_build_env_exits_when_a_compiler_is_absent` | A compiler missing from the build PATH should fail naming the variable. |
| `test_make_clean_build_env_refuses_a_conda_compiler` | A compiler inside a conda environment should be refused, not used. |
| `test_make_clean_build_env_refuses_a_system_path_symlink_into_conda` | A compiler symlink must be judged by its target, not its innocent name. |
| `test_truncate_sad_conf_keeps_seventy_lines_and_the_original` | sad.conf should be cut to the lines KEK's instructions call for. |
| `test_truncate_sad_conf_leaves_a_correctly_truncated_tree_alone` | A reused tree already prepared correctly should be left as it is. |
| `test_truncate_sad_conf_repairs_an_interrupted_preparation` | A backup with a sad.conf that does not match it should be repaired. |
| `test_truncate_sad_conf_leaves_no_staging_file_behind` | The atomic write should leave nothing beside the files it replaces. |
| `test_truncate_sad_conf_exits_when_the_tree_has_no_sad_conf` | A tree without sad.conf should fail here, not deep inside make. |
| `test_install_sad_linux_stops_before_cloning_when_dependencies_are_missing` | A missing dependency should stop the install before SAD is fetched. |
| `test_install_sad_linux_runs_every_stage_in_order` | The install should check, build, then install the launcher. |
| `test_the_linux_install_writes_a_launcher_that_runs` | The launcher the Linux install writes should run as written. |
| `test_the_dependency_report_names_packages_without_a_privileged_command` | The report should name packages, never a command to run as root. |
| `test_yacc_is_named_per_family_because_bison_does_not_supply_it_everywhere` | The package that provides yacc differs between families. |

### `test_macos_installer.py`

Covers the macOS-specific parts: read-only dependency probes, the missing-
dependency report, the sanitised build PATH, the Xcode toolchain
environment, and the order of the full installation sequence. Every
subprocess call is monkeypatched.

Build-time commands are probed on exactly the PATH the build receives, so a
command supplied only by conda is reported missing rather than disappearing
once the build starts. The non-mutating policy guard lives in
`test_installer_helpers.py`, where it covers every module in the package
rather than one platform's.

| Test | What it asserts |
|------|-----------------|
| `test_brew_prefix_returns_none_when_the_formula_is_absent` | A failed prefix lookup should report absence, never install anything. |
| `test_brew_prefix_returns_none_when_homebrew_cannot_be_run` | An absent brew executable should report absence, not raise. |
| `test_check_xcode_clt_passes_when_the_tools_are_configured` | A configured toolchain should report nothing missing. |
| `test_check_xcode_clt_reports_the_command_that_installs_them` | Unconfigured Command Line Tools should be reported naming the fix. |
| `test_check_xcode_clt_rejects_a_selection_whose_xcrun_fails` | A selected developer directory is not proof that its toolchain works. |
| `test_resolve_xcode_toolchain_rejects_an_empty_result` | An xcrun success with no path must not pass the dependency audit. |
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
| `test_install_sad_macos_stops_before_cloning_when_xcrun_is_broken` | A broken selected Xcode must be caught before source installation starts. |
| `test_make_clean_build_env_exits_when_a_tool_path_does_not_exist` | A toolchain variable pointing nowhere should fail before the build. |
| `test_make_clean_build_env_reports_an_xcrun_failure_without_a_traceback` | A toolchain race after the audit should still fail as a concise CLI error. |
| `test_make_clean_build_env_exits_when_homebrew_has_no_prefix` | An unusable Homebrew should fail naming the prefix, not crash later. |
| `test_install_sad_macos_runs_every_stage_in_order` | The install should check dependencies, build, then install the launcher. |

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

It runs `sad2xs-install-sad`, so it exercises whichever platform installer the
running machine dispatches to. On Linux that is `install_sad_linux`, and this
is the only test that covers it end to end.

Linux was validated by running the console script as an unprivileged user in
disposable containers, with the system packages provisioned by the container
rather than by the installer. Both runs cloned SAD, prepared `sad.conf`, built
it, and ran the smoke lattice through the generated launcher, leaving the shell
startup files unchanged. Last run 2026-08-27 on linux/arm64: `ubuntu:24.04` and
`almalinux:9`, both passed.

Last run: 2026-08-28, macOS 26.6.2 (Darwin 25.6.0), arm64, from the `xsuite`
conda environment with `DEVELOPER_DIR=/Library/Developer/CommandLineTools`.
Passed in 202 s: clone into a staging directory, swap into place, `make depend`,
`make exe`, a runnable `src/bin/gs`, and the smoke lattice completing with
return code 0 through the generated launcher invoked from an unrelated working
directory. Both shell rc files were unchanged, checked for modification and
for creation.

---
Part of the SAD2XS project — the unofficial Strategic Accelerator Design (SAD) to Xsuite converter.
SPDX-License-Identifier: Apache-2.0
