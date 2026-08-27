"""
================================================================================
Tests for sad2xs.install_sad._helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-29
================================================================================
"""
################################################################################
# Required Packages
################################################################################
import ast
import io
import os
import shutil
import subprocess
import tokenize
import sys
from pathlib import Path

import pytest

from sad2xs.install_sad import _helpers

################################################################################
# Shared Configuration Builder
################################################################################
def make_config(
        tmp_path,
        reuse_clone     = False,
        bin_dir         = None,
        branch          = "master",
        branch_explicit = False) -> _helpers.InstallConfig:
    """
    Build an InstallConfig rooted under a temporary directory.

    Parameters
    ----------
    tmp_path : Path
        pytest temporary directory.
    reuse_clone : bool, optional
        Value for the `reuse_clone` field. Defaults to False.
    bin_dir : Path, optional
        Launcher directory. Defaults to `tmp_path/.local/bin`.
    branch : str, optional
        Branch to request. Defaults to "master".
    branch_explicit : bool, optional
        Whether the branch came from the user. Defaults to False.

    Returns
    -------
    InstallConfig
        Configuration for use in a test.
    """
    return _helpers.InstallConfig(
        prefix          = tmp_path / "share",
        bin_dir         = bin_dir if bin_dir is not None else tmp_path / ".local" / "bin",
        repo_url        = "https://example.invalid/SAD.git",
        branch          = branch,
        branch_explicit = branch_explicit,
        reuse_clone     = reuse_clone)

################################################################################
# Install Configuration
################################################################################

########################################
# Path Derivation
########################################
@pytest.mark.parametrize(
    ("attribute", "relative_path"),
    [
        ("src_dir",     ("share", "src")),
        ("log_dir",     ("share", "logs")),
        ("build_log",   ("share", "logs", "build.log")),
        ("executable",  ("share", "src", "bin", "gs"))])
def test_install_config_derives_prefix_paths(tmp_path, attribute, relative_path):
    """
    Every build path should follow from the prefix alone.
    """
    config = make_config(tmp_path)

    assert getattr(config, attribute) == tmp_path.joinpath(*relative_path), (
        f"{attribute} should be derived from the configured prefix.")


def test_install_config_puts_the_launcher_in_the_bin_directory(tmp_path):
    """
    The launcher follows bin_dir, not the prefix, so the two move apart.
    """
    config = make_config(tmp_path)

    assert config.launcher == tmp_path / ".local" / "bin" / "sad", (
        "The launcher should sit in bin_dir, not under the prefix.")


########################################
# Path Normalisation
########################################
def test_install_config_makes_a_relative_prefix_absolute(tmp_path, monkeypatch):
    """
    A relative --prefix must not reach the launcher script.

    write_launcher bakes src_dir into a script that runs from any working
    directory, so a relative path yields a launcher that works only from
    the directory it was installed from.
    """
    monkeypatch.chdir(tmp_path)

    config = _helpers.InstallConfig(
        prefix          = Path("relative_prefix"),
        bin_dir         = Path("relative_bin"),
        repo_url        = "https://example.invalid/SAD.git",
        branch          = "master",
        branch_explicit = False,
        reuse_clone     = False)

    assert config.src_dir.is_absolute(), (
        "A relative prefix should be resolved before it reaches the launcher.")
    assert config.launcher.is_absolute(), (
        "A relative bin directory should be resolved too.")

################################################################################
# Command Runner
################################################################################

########################################
# Return Code Handling
########################################
def test_run_raises_command_error_on_nonzero_return_code(monkeypatch):
    """
    run should raise CommandError when a checked command returns non-zero.
    """
    monkeypatch.setattr(
        _helpers.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 7))

    with pytest.raises(_helpers.CommandError) as exc_info:
        _helpers.run(["sad-build-step"])

    assert exc_info.value.returncode == 7, (
        "CommandError should report the subprocess return code.")


def test_run_check_false_returns_completed_process_on_nonzero(monkeypatch):
    """
    run should return the CompletedProcess when check=False.
    """
    completed = subprocess.CompletedProcess(["sad-build-step"], 7)
    monkeypatch.setattr(_helpers.subprocess, "run", lambda cmd, **kwargs: completed)

    assert _helpers.run(["sad-build-step"], check = False) is completed, (
        "run(check=False) should return the subprocess result without raising.")


########################################
# Logged Command Failure
########################################
def test_run_raises_with_the_log_path_when_a_logged_command_fails(tmp_path):
    """
    A failed build step should carry the log that explains it.

    This is the path a real build failure takes, and the log path is the
    only pointer the user gets to the full output.
    """
    log_path = tmp_path / "build.log"
    failing  = tmp_path / "fail.py"
    failing.write_text("import sys\nprint('context line')\nsys.exit(3)\n")

    with pytest.raises(_helpers.CommandError) as exc_info:
        _helpers.run([sys.executable, str(failing)], log_path = log_path)

    assert exc_info.value.returncode == 3, (
        "The reported return code should be the command's own.")
    assert str(log_path) in str(exc_info.value), (
        "The error message should name the log file.")
    assert "context line" in log_path.read_text(), (
        "Output should reach the log even when the command fails.")


def test_run_survives_build_output_that_is_not_valid_utf8(tmp_path):
    """
    A compiler in a non-UTF-8 locale should not kill the build.
    """
    emitter = tmp_path / "emit.py"
    emitter.write_text('import sys\nsys.stdout.buffer.write(b"warn: \\xff\\xfe bad\\n")\n')
    log_path = tmp_path / "build.log"

    returncode = _helpers.run([sys.executable, str(emitter)], log_path = log_path)

    assert returncode == 0, "The command itself succeeded and should report so."
    assert "warn:" in log_path.read_text(), (
        "Undecodable bytes should be replaced, not abort the build.")


########################################
# Log Tail Reporting
########################################
def test_log_tail_reports_the_end_of_a_long_log(tmp_path, caplog):
    """
    A build failure should surface the end of the log, where the cause is.
    """
    log_path = tmp_path / "build.log"
    log_path.write_text("\n".join(f"line {n}" for n in range(500)) + "\n")

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers._log_tail(log_path, n_lines = 5)

    assert "line 499" in caplog.text, (
        "The tail should include the final line of the log.")
    assert "line 400" not in caplog.text, (
        "The tail should be limited to the requested number of lines.")


def test_log_tail_reports_a_missing_log_without_raising(tmp_path, caplog):
    """
    A log that was never created must not mask the build failure itself.
    """
    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers._log_tail(tmp_path / "absent.log")

    assert "could not read log" in caplog.text, (
        "A missing log should be reported, not raised.")

################################################################################
# Source Tree Safety
################################################################################

########################################
# Foreign Directory Protection
########################################
def test_clone_sad_refuses_to_delete_a_source_tree_it_does_not_own(
        tmp_path,
        monkeypatch):
    """
    An unrelated <prefix>/src must never be removed.

    Nothing stops a user pointing --prefix at a directory that already
    holds their own `src`, and a reinstall would otherwise delete it
    without ever saying so.
    """
    config = make_config(tmp_path)
    precious = config.src_dir / "someone_elses_work.txt"
    precious.parent.mkdir(parents = True)
    precious.write_text("not the installer's")

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert precious.exists(), (
        "A source tree this installer does not own must be left alone.")
    assert "was not created by this installer" in str(exc_info.value), (
        "The refusal should say why the directory was left in place.")


def test_a_marker_beside_the_source_tree_does_not_authorise_deleting_it(
        tmp_path,
        monkeypatch):
    """
    Ownership must be proved by the tree itself, not by its parent.

    A marker in the prefix outlives the tree it described, so it would
    authorise deleting whatever later occupied that path.
    """
    config = make_config(tmp_path)
    precious = config.src_dir / "someone_elses_work.txt"
    precious.parent.mkdir(parents = True)
    precious.write_text("not the installer's")

    # The old contract's location: beside src rather than inside it.
    (config.prefix / _helpers.INSTALL_MARKER).touch()

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit):
        _helpers.clone_sad(config)

    assert precious.exists(), (
        "A marker outside the source tree must not authorise deleting it.")


def test_clone_sad_replaces_a_tree_it_marked_as_its_own(tmp_path, monkeypatch):
    """
    The marker inside a source tree identifies it as safe to replace.
    """
    config = make_config(tmp_path)
    stale = config.src_dir / "stale.txt"
    stale.parent.mkdir(parents = True)
    stale.touch()
    config.marker.touch()

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    reused = _helpers.clone_sad(config)

    assert not stale.exists(), (
        "A tree carrying this installer's marker should be replaced.")
    assert config.marker.is_file(), (
        "The replacement tree should carry the marker for the next rerun.")
    assert reused is False, (
        "Replacing a tree is a fresh clone, so it reports no reuse.")


########################################
# Failed Install Leaves The Old Tree
########################################
def test_a_failed_clone_leaves_the_previous_source_tree_untouched(
        tmp_path,
        monkeypatch):
    """
    A clone that fails must not cost the user a working installation.

    The old tree is only removed once a complete clone exists to put in
    its place.
    """
    config = make_config(tmp_path)
    working = config.src_dir / "working_build.txt"
    working.parent.mkdir(parents = True)
    working.write_text("a good install")
    config.marker.touch()

    def failing_run(*args, **kwargs):
        raise _helpers.CommandError(["git", "clone"], 128)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", failing_run)

    with pytest.raises(_helpers.CommandError):
        _helpers.clone_sad(config)

    assert working.read_text() == "a good install", (
        "A failed clone should leave the previous source tree in place.")
    assert not list(config.prefix.glob(".src-staging-*")), (
        "A failed clone should not leave a staging directory behind.")


def test_a_failed_clone_leaves_no_ownership_marker(tmp_path, monkeypatch):
    """
    A half-finished install must not claim ownership of anything.

    A marker written before the clone would authorise deleting whatever
    the user put there afterwards.
    """
    config = make_config(tmp_path)

    def failing_run(*args, **kwargs):
        raise _helpers.CommandError(["git", "clone"], 128)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", failing_run)

    with pytest.raises(_helpers.CommandError):
        _helpers.clone_sad(config)

    assert not list(config.prefix.rglob(_helpers.INSTALL_MARKER)), (
        "No ownership marker should survive a failed clone.")


def test_an_absent_explicit_branch_leaves_the_previous_source_tree_untouched(
        tmp_path,
        monkeypatch):
    """
    A typo in --branch must be reported before anything is deleted.

    Validating the request only after removing the old tree would destroy
    a working installation to report a typo.
    """
    config = make_config(tmp_path, branch = "typoo", branch_explicit = True)
    working = config.src_dir / "working_build.txt"
    working.parent.mkdir(parents = True)
    working.write_text("a good install")
    config.marker.touch()

    monkeypatch.setattr(
        _helpers.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, _helpers.NO_MATCHING_REF, stderr = ""))
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit):
        _helpers.clone_sad(config)

    assert working.read_text() == "a good install", (
        "A refused branch should leave the previous source tree in place.")


########################################
# Prefix Guard
########################################
def test_guard_prefix_catches_a_home_directory_reached_through_a_symlink(
        tmp_path,
        monkeypatch):
    """
    A symlinked home must still be refused as an install prefix.

    Comparing a resolved prefix against an unresolved home fails open, and
    home is commonly a symlink on network filesystems such as AFS.
    """
    real_home = tmp_path / "real_home"
    real_home.mkdir()
    link_home = tmp_path / "link_home"
    link_home.symlink_to(real_home)

    monkeypatch.setattr(_helpers.Path, "home", classmethod(lambda cls: link_home))

    config = _helpers.InstallConfig(
        prefix          = link_home,
        bin_dir         = tmp_path / "bin",
        repo_url        = "https://example.invalid/SAD.git",
        branch          = "master",
        branch_explicit = False,
        reuse_clone     = False)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert "Refusing to install into" in str(exc_info.value), (
        "A symlinked home should be refused like any other home directory.")

################################################################################
# Source Selection
################################################################################

########################################
# Explicit Branch
########################################
def test_clone_sad_fails_when_an_explicitly_named_branch_is_absent(
        tmp_path,
        monkeypatch):
    """
    A mistyped --branch should stop the install, not install other source.

    Falling back would turn a typo into a successful build of a branch the
    user never asked for, reported as success.
    """
    config = make_config(tmp_path, branch = "typoo", branch_explicit = True)

    monkeypatch.setattr(
        _helpers.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 2))
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert "typoo" in str(exc_info.value), (
        "The message should name the branch that was not found.")


########################################
# Default Branch Fallback
########################################
def test_clone_sad_falls_back_to_the_remote_default_branch(tmp_path, monkeypatch):
    """
    The default branch name only should tolerate an upstream rename.

    Nobody asked for "master" by name, so a remote that renamed its default
    must not break every install.
    """
    config = make_config(tmp_path, branch = "master", branch_explicit = False)

    commands = []
    monkeypatch.setattr(
        _helpers.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 2))
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: commands.append(cmd))

    _helpers.clone_sad(config)

    assert "--branch" not in commands[0], (
        "An absent default branch should defer to the remote's own default.")


########################################
# Remote Query Failures
########################################
def test_clone_sad_reports_a_remote_failure_as_a_remote_failure(
        tmp_path,
        monkeypatch):
    """
    A network or repository failure is not an absent branch.

    Reporting it as one would send the user hunting for a typo in a branch
    name that is perfectly correct.
    """
    config = make_config(tmp_path, branch = "master", branch_explicit = True)

    monkeypatch.setattr(
        _helpers.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, 128, stderr = "fatal: could not read Username"))

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    message = str(exc_info.value)

    assert "could not read Username" in message, (
        "Git's own diagnostic should reach the user.")
    assert "does not exist" not in message, (
        "A remote that could not be queried must not be reported as a "
        "missing branch.")


def test_clone_sad_reports_a_git_that_cannot_be_run(tmp_path, monkeypatch):
    """
    A missing git should say so rather than surface as a traceback.
    """
    config = make_config(tmp_path)

    def no_git(cmd, **kwargs):
        raise OSError(2, "No such file or directory")

    monkeypatch.setattr(_helpers.subprocess, "run", no_git)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert "Could not run git" in str(exc_info.value), (
        "A git that will not run should be reported as such.")


########################################
# Reuse Validation
########################################
@pytest.mark.parametrize(
    ("origin", "described"),
    [
        (None, "unreadable"),
        ("https://example.invalid/somethingelse.git", "somethingelse.git")])
def test_clone_sad_refuses_to_reuse_a_checkout_whose_origin_is_not_the_request(
        tmp_path,
        monkeypatch,
        origin,
        described):
    """
    Reuse validation fails closed on anything that is not a match.

    An unreadable origin, an empty .git, or a git that will not run all
    look the same, and none of them prove the tree holds the requested
    source.
    """
    config = make_config(tmp_path, reuse_clone = True)
    (config.src_dir / ".git").mkdir(parents = True)

    monkeypatch.setattr(_helpers, "_git_value", lambda src_dir, *args: origin)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert described in str(exc_info.value), (
        "The refusal should say what was found instead of the request.")


@pytest.mark.parametrize("branch", [None, "HEAD"])
def test_clone_sad_refuses_to_reuse_a_checkout_with_no_usable_branch(
        tmp_path,
        monkeypatch,
        branch):
    """
    An unreadable or detached HEAD cannot satisfy an explicit --branch.

    A detached checkout reports "HEAD", which is never a branch a user
    asked for by name.
    """
    config = make_config(
        tmp_path,
        reuse_clone     = True,
        branch          = "wanted",
        branch_explicit = True)
    (config.src_dir / ".git").mkdir(parents = True)

    monkeypatch.setattr(
        _helpers,
        "_git_value",
        lambda src_dir, *args: config.repo_url if args[0] == "remote" else branch)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.clone_sad(config)

    assert "not 'wanted'" in str(exc_info.value), (
        "The refusal should name the branch that was requested.")


def test_clone_sad_keeps_a_matching_tree_and_reports_the_reuse(
        tmp_path,
        monkeypatch):
    """
    A matching checkout should be kept, and the reuse reported.

    The build reads the reuse answer to decide whether to clean first.
    """
    config = make_config(tmp_path, reuse_clone = True)
    (config.src_dir / ".git").mkdir(parents = True)
    marker = config.src_dir / "already_here.txt"
    marker.touch()

    monkeypatch.setattr(_helpers, "_git_value", lambda src_dir, *args: config.repo_url)
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda *args, **kwargs: pytest.fail("clone_sad should not clone here"))

    assert _helpers.clone_sad(config) is True, (
        "A reused tree should be reported so the build cleans it first.")
    assert marker.exists(), (
        "Reusing a clone should leave the existing source tree untouched.")


def test_clone_sad_reports_no_reuse_when_asked_to_reuse_a_tree_that_is_absent(
        tmp_path,
        monkeypatch):
    """
    --reuse-clone with nothing to reuse is still a fresh clone.

    The build reads this to decide whether to run make clean first, and
    upstream's clean target returns non-zero on a tree with nothing to
    remove.
    """
    config = make_config(tmp_path, reuse_clone = True)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    assert _helpers.clone_sad(config) is False, (
        "Asking to reuse a tree that does not exist should still clone.")


########################################
# Build Log Freshness
########################################
def test_clone_sad_truncates_the_build_log_even_when_reusing_a_tree(
        tmp_path,
        monkeypatch):
    """
    A reused tree must still start from an empty build log.

    Otherwise a failed rebuild reports the tail of an accumulated log,
    which can show an earlier run's error rather than this one's.
    """
    config = make_config(tmp_path, reuse_clone = True)
    (config.src_dir / ".git").mkdir(parents = True)
    config.log_dir.mkdir(parents = True)
    config.build_log.write_text("error from a previous build\n")

    monkeypatch.setattr(_helpers, "_git_value", lambda src_dir, *args: config.repo_url)
    monkeypatch.setattr(_helpers, "run", lambda *args, **kwargs: None)

    _helpers.clone_sad(config)

    assert config.build_log.read_text() == "", (
        "Reusing a source tree should still start a fresh build log.")

################################################################################
# Build
################################################################################

########################################
# Clean Target Selection
########################################
@pytest.mark.parametrize(
    ("reused_tree", "expected_targets"),
    [
        (False, ["depend", "exe"]),
        (True,  ["clean", "depend", "exe"])])
def test_make_sad_cleans_only_a_reused_tree(
        tmp_path,
        monkeypatch,
        reused_tree,
        expected_targets):
    """
    A fresh clone has nothing to clean, and upstream's clean target fails
    when there is nothing to remove.
    """
    config = make_config(tmp_path)

    targets = []
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: targets.append(cmd[1]))

    _helpers.make_sad(config, env = {}, reused_tree = reused_tree)

    assert targets == expected_targets, (
        "The clean step should run only where there is something to clean.")


########################################
# Build Verification
########################################
def test_verify_executable_accepts_an_executable_binary(tmp_path):
    """
    A build that produced a runnable binary should pass without exiting.
    """
    config = make_config(tmp_path)
    config.executable.parent.mkdir(parents = True)
    config.executable.touch()
    config.executable.chmod(0o755)

    _helpers.verify_executable(config)


def test_verify_executable_rejects_a_binary_without_the_executable_bit(tmp_path):
    """
    A file that exists but cannot be run is a failed build.
    """
    config = make_config(tmp_path)
    config.executable.parent.mkdir(parents = True)
    config.executable.touch()
    config.executable.chmod(0o644)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.verify_executable(config)

    assert "not executable" in str(exc_info.value), (
        "A present but unrunnable binary should be reported as a failed build.")


def test_verify_executable_exits_when_the_build_produced_no_binary(tmp_path):
    """
    A build that returns zero but leaves no binary should still fail.
    """
    config = make_config(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.verify_executable(config)

    assert str(config.build_log) in str(exc_info.value), (
        "The message should point at the build log.")

################################################################################
# Launcher
################################################################################
def test_write_launcher_writes_an_executable_script(tmp_path):
    """
    write_launcher should create an executable script pointing at the build.
    """
    config = make_config(tmp_path)

    _helpers.write_launcher(config)

    assert config.launcher.stat().st_mode & 0o111, (
        "write_launcher should make the launcher executable.")
    assert 'GS_EXEC="$SAD_DIR/bin/gs"' in config.launcher.read_text(), (
        "Launcher should execute SAD's gs binary.")


def test_write_launcher_quotes_a_prefix_containing_shell_metacharacters(tmp_path):
    """
    An awkward prefix should reach the launcher as a literal path.

    The prefix is user-supplied and lands inside shell source, so a quote,
    backtick or $( ) would break the script or be evaluated at run time.
    """
    config = make_config(tmp_path)
    awkward = tmp_path / 'we"ird$(echo pwned)`id` dir'
    config = _helpers.InstallConfig(
        prefix          = awkward,
        bin_dir         = tmp_path / "bin",
        repo_url        = config.repo_url,
        branch          = "master",
        branch_explicit = False,
        reuse_clone     = False)

    _helpers.write_launcher(config)

    sad_dir_line = next(
        line for line in config.launcher.read_text().splitlines()
        if line.startswith("SAD_DIR="))
    resolved = subprocess.run(
        ["bash", "-c", f'{sad_dir_line}\nprintf "%s" "$SAD_DIR"'],
        capture_output = True,
        text           = True,
        check          = True)

    assert resolved.stdout == str(config.src_dir), (
        "The launcher should resolve the prefix literally, evaluating nothing.")

################################################################################
# PATH Reporting
################################################################################
def test_report_path_setup_is_quiet_when_the_directory_is_on_path(
        tmp_path,
        monkeypatch,
        caplog):
    """
    A launcher directory already on PATH needs nothing from the user.
    """
    config = make_config(tmp_path)

    monkeypatch.setenv("PATH", os.pathsep.join(["/usr/bin", str(config.bin_dir)]))

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    assert "already on PATH" in caplog.text, (
        "A reachable launcher directory should be confirmed as such.")
    assert "export PATH" not in caplog.text, (
        "No instruction is needed when the directory is already reachable.")


def _printed_export_line(caplog) -> str:
    """
    Return the export instruction report_path_setup printed.

    Parameters
    ----------
    caplog : pytest LogCaptureFixture
        Captured log output.

    Returns
    -------
    str
        The single line beginning `export PATH=`.
    """
    return next(
        line.strip() for line in caplog.text.splitlines()
        if line.strip().startswith("export PATH="))


def test_report_path_setup_prints_the_export_without_touching_any_rc_file(
        tmp_path,
        monkeypatch,
        caplog):
    """
    An unreachable launcher directory should be reported, never wired up.

    Editing shell configuration is invasive, and a throwaway --bin-dir
    would leave a permanent entry behind pointing at a directory that need
    not outlive the shell.
    """
    config = make_config(tmp_path)

    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr(_helpers.Path, "home", classmethod(lambda cls: tmp_path))

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    assert str(config.bin_dir) in _printed_export_line(caplog), (
        "The user should be told the exact line to add.")
    assert not (tmp_path / ".zshrc").exists(), (
        "No shell configuration file should be created.")
    assert not (tmp_path / ".bashrc").exists(), (
        "No shell configuration file should be created.")


########################################
# Quoting Of The Printed Instruction
########################################
def test_report_path_setup_prints_an_export_a_shell_can_run(
        tmp_path,
        monkeypatch,
        caplog):
    """
    The printed line is meant to be pasted, so it must run as printed.

    A launcher directory containing shell metacharacters would otherwise
    produce an instruction that breaks or evaluates when pasted, which is
    the same defect the launcher script itself had.
    """
    awkward = tmp_path / 'we"ird$(echo pwned)`id` dir'
    config = make_config(tmp_path, bin_dir = awkward)

    # Resolved before PATH is narrowed, or the interpreter is unfindable.
    bash = shutil.which("bash") or "/bin/bash"
    monkeypatch.setenv("PATH", "/usr/bin")

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    export_line = _printed_export_line(caplog)
    resolved = subprocess.run(
        [bash, "-c", f'PATH=/usr/bin\n{export_line}\nprintf "%s" "${{PATH%%:*}}"'],
        capture_output  = True,
        text            = True,
        check           = True)

    assert resolved.stdout == str(config.bin_dir), (
        "The pasted instruction should put the literal directory on PATH, "
        "evaluating nothing.")


################################################################################
# Non-Mutating Policy
################################################################################
########################################
# Modules On The Execution Path
########################################
def installer_modules() -> list[Path]:
    """
    List every module the console script can reach.

    Returns
    -------
    list of Path
        Every Python file in the installer package.

    Notes
    -----
    Guarding only the platform modules would miss shared code, which every
    platform imports and runs.
    """
    package = Path(_helpers.__file__).parent
    modules = sorted(package.glob("*.py"))

    assert len(modules) >= 4, (
        f"The installer package modules should have been found: {package}")
    return modules


########################################
# Source Text
########################################
def test_no_installer_module_has_a_package_installation_path():
    """
    No installer source line may name a command that installs packages.

    The installer is only allowed to report what is missing. Executing a
    package manager would ask the user for a password for work they never
    authorised, and shared code runs on every platform.
    """
    forbidden = (
        "sudo", "apt", "apt-get", "dnf", "yum", "zypper", "pacman",
        "brew install")

    offenders = []
    for module in installer_modules():
        source = module.read_text(encoding = "utf-8")

        # Package names and manual instructions are quoted on purpose, so
        # only what the interpreter would execute is inspected.
        code = "".join(
            token.string for token in tokenize.generate_tokens(
                io.StringIO(source).readline)
            if token.type not in (
                tokenize.STRING,
                tokenize.COMMENT,
                tokenize.FSTRING_MIDDLE))

        offenders.extend(
            (module.name, phrase) for phrase in forbidden if phrase in code)

    assert offenders == [], (
        f"No installer module may execute a package manager: {offenders}")


########################################
# Launched Commands
########################################
def test_no_installer_module_runs_an_install_subcommand():
    """
    No subprocess any installer module launches may install packages.

    The literal-phrase check cannot see a command split across list
    elements, which is how a shell installer builds one.
    """
    runners = {"run", "check_output", "check_call", "call", "Popen", "system"}
    forbidden = (
        "sudo", "install", "apt", "apt-get", "dnf", "yum", "zypper", "pacman",
        "brew")

    offenders = []
    for module in installer_modules():
        for node in ast.walk(ast.parse(module.read_text(encoding = "utf-8"))):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(
                func, "id", "")
            if name not in runners:
                continue

            for argument in ast.walk(node):
                if not (isinstance(argument, ast.Constant)
                        and isinstance(argument.value, str)):
                    continue
                # A shell string carries the whole command in one constant,
                # while a list carries each word in its own.
                words = set(argument.value.split()) | {argument.value}
                offenders.extend(
                    (module.name, word) for word in forbidden if word in words)

    assert offenders == [], (
        f"No launched command may install packages: {offenders}")
