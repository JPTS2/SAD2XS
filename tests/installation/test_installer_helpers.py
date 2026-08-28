"""
================================================================================
Tests for sad2xs.install_sad._helpers
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-08-27
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
from dataclasses import replace
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
def test_prepare_source_refuses_to_delete_a_source_tree_it_does_not_own(
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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    with pytest.raises(SystemExit) as exc_info:
        _helpers.prepare_source(config)

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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    with pytest.raises(SystemExit):
        _helpers.prepare_source(config)

    assert precious.exists(), (
        "A marker outside the source tree must not authorise deleting it.")


def test_a_symlinked_source_marker_does_not_authorise_deleting_the_tree(
        tmp_path,
        monkeypatch):
    """
    Ownership must come from a regular marker inside the source tree.

    Following a marker symlink would let an unrelated file elsewhere prove
    ownership of a tree that this installer must leave alone.
    """
    config = make_config(tmp_path)
    precious = config.src_dir / "someone_elses_work.txt"
    precious.parent.mkdir(parents = True)
    precious.write_text("not the installer's", encoding = "utf-8")

    target = tmp_path / "ordinary-file"
    target.write_text("not an ownership marker", encoding = "utf-8")
    config.marker.symlink_to(target)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)

    def refuse_clone(*args, **kwargs):
        pytest.fail("an unowned tree must not be cloned")

    monkeypatch.setattr(_helpers, "run", refuse_clone)

    with pytest.raises(SystemExit):
        _helpers.prepare_source(config)

    assert precious.read_text(encoding = "utf-8") == "not the installer's", (
        "A symlinked marker must not authorise replacing the source tree.")
    assert config.marker.is_symlink(), (
        "The marker symlink itself must be left in place.")
    assert target.read_text(encoding = "utf-8") == "not an ownership marker", (
        "The marker target must not be touched.")


def test_prepare_source_holds_the_previous_tree_aside_rather_than_deleting_it(
        tmp_path,
        monkeypatch):
    """
    A replacement clone must keep the previous tree recoverable.

    SAD bakes its build directory into the binary, so the clone has to
    land at the final path. Holding the previous tree aside is what makes
    a failed build recoverable anyway.
    """
    config = make_config(tmp_path)
    stale = config.src_dir / "stale.txt"
    stale.parent.mkdir(parents = True)
    stale.touch()
    config.marker.touch()

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True))

    reused = _helpers.prepare_source(config)

    assert reused is False, (
        "Replacing a tree is a fresh clone, so it reports no reuse.")
    assert (config.backup_dir / "stale.txt").is_file(), (
        "The previous tree should be held aside, not deleted.")
    assert not stale.exists(), (
        "The clone should land at the final source path.")
    assert config.marker.is_file(), (
        "A complete clone should be marked, or the next run cannot replace "
        "what an interrupted one left behind.")


def test_prepare_source_restores_the_previous_tree_when_the_clone_fails(
        tmp_path,
        monkeypatch):
    """
    A failed clone should put the previous tree straight back.
    """
    config = make_config(tmp_path)
    kept = config.src_dir / "kept.txt"
    kept.parent.mkdir(parents = True)
    kept.touch()
    config.marker.touch()

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)

    def failing_clone(cmd, **kwargs):
        raise _helpers.CommandError(cmd, 128)

    monkeypatch.setattr(_helpers, "run", failing_clone)

    with pytest.raises(_helpers.CommandError):
        _helpers.prepare_source(config)

    assert kept.is_file(), (
        "A failed clone should leave the previous tree exactly where it was.")
    assert list(config.prefix.glob(".src-previous-*")) == [], (
        "Nothing should be left held aside once the tree is restored.")


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
        _helpers.prepare_source(config)

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
        _helpers.prepare_source(config)

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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    with pytest.raises(SystemExit):
        _helpers.prepare_source(config)

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
        _helpers.prepare_source(config)

    assert "Refusing to install into" in str(exc_info.value), (
        "A symlinked home should be refused like any other home directory.")

################################################################################
# Source Selection
################################################################################

########################################
# Explicit Branch
########################################
def test_prepare_source_fails_when_an_explicitly_named_branch_is_absent(
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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    with pytest.raises(SystemExit) as exc_info:
        _helpers.prepare_source(config)

    assert "typoo" in str(exc_info.value), (
        "The message should name the branch that was not found.")


########################################
# Default Branch Fallback
########################################
def test_prepare_source_falls_back_to_the_remote_default_branch(tmp_path, monkeypatch):
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
    def record_clone(cmd, **kwargs):
        commands.append(cmd)
        Path(cmd[-1]).mkdir(parents = True, exist_ok = True)

    monkeypatch.setattr(_helpers, "run", record_clone)

    _helpers.prepare_source(config)

    assert "--branch" not in commands[0], (
        "An absent default branch should defer to the remote's own default.")


########################################
# Remote Query Failures
########################################
def test_prepare_source_reports_a_remote_failure_as_a_remote_failure(
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
        _helpers.prepare_source(config)

    message = str(exc_info.value)

    assert "could not read Username" in message, (
        "Git's own diagnostic should reach the user.")
    assert "does not exist" not in message, (
        "A remote that could not be queried must not be reported as a "
        "missing branch.")


def test_prepare_source_reports_a_git_that_cannot_be_run(tmp_path, monkeypatch):
    """
    A missing git should say so rather than surface as a traceback.
    """
    config = make_config(tmp_path)

    def no_git(cmd, **kwargs):
        raise OSError(2, "No such file or directory")

    monkeypatch.setattr(_helpers.subprocess, "run", no_git)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.prepare_source(config)

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
def test_prepare_source_refuses_to_reuse_a_checkout_whose_origin_is_not_the_request(
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
        _helpers.prepare_source(config)

    assert described in str(exc_info.value), (
        "The refusal should say what was found instead of the request.")


@pytest.mark.parametrize("branch", [None, "HEAD"])
def test_prepare_source_refuses_to_reuse_a_checkout_with_no_usable_branch(
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
        _helpers.prepare_source(config)

    assert "not 'wanted'" in str(exc_info.value), (
        "The refusal should name the branch that was requested.")


def test_prepare_source_keeps_a_matching_tree_and_reports_the_reuse(
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
        lambda *args, **kwargs: pytest.fail("prepare_source should not clone here"))

    assert _helpers.prepare_source(config) is True, (
        "A reused tree should be reported so the build cleans it first.")
    assert marker.exists(), (
        "Reusing a clone should leave the existing source tree untouched.")


def test_prepare_source_reports_no_reuse_when_asked_to_reuse_a_tree_that_is_absent(
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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    assert _helpers.prepare_source(config) is False, (
        "Asking to reuse a tree that does not exist should still clone.")


########################################
# Build Log Freshness
########################################
def test_prepare_source_truncates_the_build_log_even_when_reusing_a_tree(
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
    monkeypatch.setattr(
        _helpers,
        "run",
        lambda cmd, **kwargs: Path(cmd[-1]).mkdir(parents = True, exist_ok = True))

    _helpers.prepare_source(config)

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

    _helpers.make_sad(
        config,
        env         = {},
        reused_tree = reused_tree,
        work_dir    = config.src_dir)

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

    _helpers.verify_executable(config, config.src_dir)


def test_verify_executable_rejects_a_binary_without_the_executable_bit(tmp_path):
    """
    A file that exists but cannot be run is a failed build.
    """
    config = make_config(tmp_path)
    config.executable.parent.mkdir(parents = True)
    config.executable.touch()
    config.executable.chmod(0o644)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.verify_executable(config, config.src_dir)

    assert "not executable" in str(exc_info.value), (
        "A present but unrunnable binary should be reported as a failed build.")


def test_verify_executable_exits_when_the_build_produced_no_binary(tmp_path):
    """
    A build that returns zero but leaves no binary should still fail.
    """
    config = make_config(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.verify_executable(config, config.src_dir)

    assert str(config.build_log) in str(exc_info.value), (
        "The message should point at the build log.")

################################################################################
# Install Transaction
################################################################################
def _working_installation(tmp_path) -> tuple:
    """
    Build a config with a working source tree and launcher already in place.

    Parameters
    ----------
    tmp_path : Path
        Directory to root the installation under.

    Returns
    -------
    tuple
        The config and the bytes of the launcher that is already there.
    """
    config = make_config(tmp_path)
    config.executable.parent.mkdir(parents = True)
    config.executable.write_text("previous gs\n", encoding = "utf-8")
    config.executable.chmod(0o755)
    config.marker.touch()
    (config.src_dir / ".git").mkdir()

    _helpers.write_launcher(config)
    return config, config.launcher.read_bytes()


def _open_transaction(config, had_previous: bool) -> None:
    """
    Recreate the transaction state a killed run would have left.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    had_previous : bool
        Whether a source tree existed when that run began.
    """
    config.transaction_dir.mkdir(parents = True, exist_ok = True)
    _helpers._write_transaction_record(config, had_previous)


def _cloning_run(failing_stage: str = ""):
    """
    Build a stand-in for `run` that clones and builds on the filesystem.

    Parameters
    ----------
    failing_stage : str, optional
        Stage to fail: "clone", "make depend", or "make exe". Defaults to
        succeeding at every stage.

    Returns
    -------
    callable
        A replacement for `_helpers.run`.
    """
    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            if failing_stage == "clone":
                raise _helpers.CommandError(cmd, 128)
            Path(cmd[-1]).mkdir(parents = True, exist_ok = True)
            return None
        if " ".join(cmd) == failing_stage:
            raise _helpers.CommandError(cmd, 2)
        return None

    return fake_run


def _building_prepare(config, failing_stage: str = ""):
    """
    Build a preparation step that produces the new SAD binary.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    failing_stage : str, optional
        "prepare" to fail here, "verify" to leave no binary behind.
        Defaults to producing a working binary.

    Returns
    -------
    callable
        A preparation callable for `install_sad_source`.
    """
    def prepare(src_dir):
        if failing_stage == "prepare":
            sys.exit("preparation failed")
        if failing_stage == "verify":
            return
        (src_dir / "bin").mkdir(parents = True, exist_ok = True)
        binary = src_dir / "bin" / "gs"
        binary.write_text("new gs\n", encoding = "utf-8")
        binary.chmod(0o755)

    return prepare


def _assert_installation_survived(config, launcher_before) -> None:
    """
    Check that a failed install left everything exactly as it was.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    launcher_before : bytes
        The launcher recorded before the failed run.
    """
    assert config.executable.read_text(encoding = "utf-8") == "previous gs\n", (
        "The working SAD binary should survive a failed install.")
    assert config.launcher.read_bytes() == launcher_before, (
        "The launcher should survive a failed install byte for byte.")
    assert not config.transaction_dir.exists(), (
        "A rolled-back install should leave no transaction behind.")


########################################
# Failure At Every Stage
########################################
@pytest.mark.parametrize(
    "failing_stage",
    ["clone", "prepare", "make depend", "make exe", "verify", "launcher"])
def test_a_failure_at_any_stage_leaves_the_previous_installation_working(
        tmp_path,
        monkeypatch,
        failing_stage):
    """
    An install that fails must cost the user nothing.

    The previous tree is held aside for the whole clone, preparation,
    build, and launcher write, and put back if any of them fails.
    """
    config, launcher_before = _working_installation(tmp_path)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run(failing_stage))

    if failing_stage == "launcher":
        real_replace = _helpers.os.replace

        def fail_launcher_replace(source, target):
            if Path(target) == config.launcher:
                raise OSError("replace failed")
            return real_replace(source, target)

        monkeypatch.setattr(_helpers.os, "replace", fail_launcher_replace)

    with pytest.raises((SystemExit, _helpers.CommandError, OSError)):
        _helpers.install_sad_source(
            config, {}, _building_prepare(config, failing_stage))

    _assert_installation_survived(config, launcher_before)


########################################
# Successful Install
########################################
def test_a_verified_install_replaces_the_previous_one_and_leaves_no_state(
        tmp_path,
        monkeypatch):
    """
    A build that passes verification should become the installation.

    This is the converse of the failure cases, and proves the rollback is
    not simply refusing to ever install anything.
    """
    config, _launcher_before = _working_installation(tmp_path)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run())

    _helpers.install_sad_source(config, {}, _building_prepare(config))

    assert config.executable.read_text(encoding = "utf-8") == "new gs\n", (
        "A verified build should replace the previous installation.")
    assert config.marker.is_file(), (
        "The installed tree should be marked as this installer's.")
    assert not config.transaction_dir.exists(), (
        "A committed install should leave no rollback or staging state.")
    assert sorted(path.name for path in config.prefix.iterdir()) == [
        "logs", "src"], "A committed install should leave nothing else behind."


########################################
# Launcher Refused Before Any Work
########################################
def test_an_unowned_launcher_is_refused_before_anything_is_cloned_or_moved(
        tmp_path,
        monkeypatch):
    """
    An unowned launcher should cost no clone, no build, and no move.

    Discovering it after the build would mean a working SAD had already
    been taken apart for an install that cannot finish.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    (config.src_dir / "previous.txt").touch()
    config.marker.touch()
    config.bin_dir.mkdir(parents = True)
    config.launcher.write_text("#!/bin/sh\nsomeone elses sad\n")

    def refuse(*args, **kwargs):
        raise AssertionError("nothing should run before the launcher check")

    monkeypatch.setattr(_helpers, "run", refuse)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.install_sad_source(config, {})

    assert "not written by this installer" in str(exc_info.value), (
        "The refusal should say why nothing was done.")
    assert (config.src_dir / "previous.txt").is_file(), (
        "The source tree should not have been moved.")
    assert not config.transaction_dir.exists(), (
        "No transaction should have been opened.")


########################################
# Cross-Process Interruption
########################################
def test_an_interrupted_install_is_recovered_by_the_next_invocation(tmp_path):
    """
    A run killed outright must not hide the working installation.

    Nothing catches SIGKILL, so recovery cannot depend on an exception. The
    transaction has a fixed name for exactly this reason.
    """
    config = make_config(tmp_path)

    # The state a killed run leaves: the previous tree held aside, and a
    # half-finished new one at src.
    _open_transaction(config, had_previous = True)
    config.backup_dir.mkdir(parents = True)
    (config.backup_dir / _helpers.INSTALL_MARKER).touch()
    (config.backup_dir / "working.txt").write_text("previous", encoding = "utf-8")
    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    (config.src_dir / "half_built.txt").touch()

    _helpers.reconcile_transaction(config)

    assert (config.src_dir / "working.txt").read_text(
        encoding = "utf-8") == "previous", (
        "The next run should put the working installation back.")
    assert not (config.src_dir / "half_built.txt").exists(), (
        "The half-finished tree should be gone.")
    assert not config.transaction_dir.exists(), (
        "Recovery should close the transaction.")


@pytest.mark.parametrize("failing_operation", ["restore", "retire"])
def test_startup_recovery_reports_filesystem_failures_with_every_state_path(
        tmp_path,
        monkeypatch,
        failing_operation):
    """
    Recovery I/O failures should be actionable without exposing a traceback.

    Source, backup, and transaction are all named because any of them may be
    the surviving copy after a filesystem operation fails part way through.
    """
    config = make_config(tmp_path)
    _open_transaction(config, had_previous = True)
    config.src_dir.mkdir(parents = True)
    config.marker.touch()

    def fail_operation(*args):
        raise OSError(f"{failing_operation} failed")

    if failing_operation == "restore":
        config.backup_dir.mkdir(parents = True)
        (config.backup_dir / _helpers.INSTALL_MARKER).touch()
        monkeypatch.setattr(_helpers, "_restore_backup", fail_operation)
    else:
        monkeypatch.setattr(_helpers, "_retire_transaction", fail_operation)

    with pytest.raises(_helpers.RollbackError) as exc_info:
        _helpers.reconcile_transaction(config)

    message = str(exc_info.value)
    assert f"Source:      {config.src_dir}" in message
    assert f"Backup:      {config.backup_dir}" in message
    assert f"Transaction: {config.transaction_dir}" in message
    assert f"{failing_operation} failed" in message
    assert config.transaction_dir.exists(), (
        "A failed recovery must leave its transaction available for inspection.")


def test_an_interruption_during_the_clone_leaves_the_source_untouched(tmp_path):
    """
    A run killed during the clone has nothing to restore.

    The clone lands in the transaction, so src still holds the previous
    tree and only the partial clone has to be discarded.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    (config.src_dir / "working.txt").write_text("previous", encoding = "utf-8")

    # A clone killed before it finished: staged, unmarked, no backup.
    _open_transaction(config, had_previous = True)
    config.staging_dir.mkdir(parents = True)
    (config.staging_dir / "partial.txt").touch()

    _helpers.reconcile_transaction(config)

    assert (config.src_dir / "working.txt").read_text(
        encoding = "utf-8") == "previous", (
        "An interrupted clone should leave the source tree alone.")
    assert not config.transaction_dir.exists(), (
        "The partial clone should be discarded.")


def test_a_fresh_invocation_recovers_an_interrupted_install(
        tmp_path,
        monkeypatch):
    """
    The next run of the installer should reconcile before doing anything.

    Recovering only when reconcile_transaction is called by hand would
    leave a killed install permanently hidden.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)

    _open_transaction(config, had_previous = True)
    config.backup_dir.mkdir(parents = True)
    (config.backup_dir / _helpers.INSTALL_MARKER).touch()
    (config.backup_dir / "bin").mkdir()
    binary = config.backup_dir / "bin" / "gs"
    binary.write_text("previous gs\n", encoding = "utf-8")
    binary.chmod(0o755)

    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    (config.src_dir / "half_built.txt").touch()

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run())

    _helpers.install_sad_source(config, {}, _building_prepare(config))

    assert not (config.src_dir / "half_built.txt").exists(), (
        "The interrupted install should have been reconciled first.")
    assert config.executable.read_text(encoding = "utf-8") == "new gs\n", (
        "The new install should then proceed to completion.")
    assert not config.transaction_dir.exists(), (
        "No transaction state should survive the committed install.")


########################################
# First Install
########################################
@pytest.mark.parametrize(
    "failing_stage",
    ["prepare", "make depend", "make exe", "verify", "launcher"])
def test_a_first_install_that_fails_leaves_nothing_behind(
        tmp_path,
        monkeypatch,
        failing_stage):
    """
    A failed first install must not leave a broken tree pretending to work.

    There is no previous installation to restore here, so rollback has to
    remove what this run created rather than assume a backup exists.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run(failing_stage))

    if failing_stage == "launcher":
        real_replace = _helpers.os.replace

        def fail_launcher_replace(source, target):
            if Path(target) == config.launcher:
                raise OSError("replace failed")
            return real_replace(source, target)

        monkeypatch.setattr(_helpers.os, "replace", fail_launcher_replace)

    with pytest.raises((SystemExit, _helpers.CommandError, OSError)):
        _helpers.install_sad_source(
            config, {}, _building_prepare(config, failing_stage))

    assert not config.src_dir.exists(), (
        "A failed first install should leave no source tree.")
    assert not config.launcher.exists(), (
        "A failed first install should leave no launcher.")
    assert not config.transaction_dir.exists(), (
        "A failed first install should leave no transaction or staging state.")
    assert list(config.bin_dir.iterdir()) == [], (
        "No staged launcher should survive in the launcher directory.")


def test_a_first_install_killed_after_activation_is_recovered(tmp_path):
    """
    A first install killed after its tree reached src must not look done.

    There is no backup in this state, so recovery cannot read the absence
    of one as "the clone never finished". The record says otherwise.
    """
    config = make_config(tmp_path)
    _open_transaction(config, had_previous = False)
    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    (config.src_dir / "half_built.txt").touch()

    _helpers.reconcile_transaction(config)

    assert not config.src_dir.exists(), (
        "A first install that never finished should be discarded.")
    assert not config.transaction_dir.exists(), (
        "Recovery should close the transaction.")


def test_a_first_install_leaves_an_unmarked_tree_alone(tmp_path):
    """
    Recovery must not delete a tree at src it cannot prove it created.
    """
    config = make_config(tmp_path)
    _open_transaction(config, had_previous = False)
    config.src_dir.mkdir(parents = True)
    (config.src_dir / "somebody_elses.txt").touch()

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    assert str(config.src_dir) in str(exc_info.value), (
        "The message should name the tree that was left alone.")
    assert (config.src_dir / "somebody_elses.txt").is_file(), (
        "An unidentifiable tree must not be removed.")


########################################
# Transaction Ownership
########################################
def test_an_unmarked_transaction_directory_is_refused_and_preserved(tmp_path):
    """
    A directory that merely shares the name is not this installer's.

    Recovery deletes what it finds, so it has to prove the directory came
    from an install of ours before touching it.
    """
    config = make_config(tmp_path)
    config.transaction_dir.mkdir(parents = True)
    (config.transaction_dir / "someone_elses.txt").write_text(
        "data", encoding = "utf-8")

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    assert str(config.transaction_dir) in str(exc_info.value), (
        "The message should name the directory that was left alone.")
    assert (config.transaction_dir / "someone_elses.txt").is_file(), (
        "An unrecognised transaction directory must be preserved.")


@pytest.mark.parametrize(
    "malformed",
    [
        "not json",
        "[]",
        '{"had_previous": true}',
        '{"version": 1, "had_previous": "yes"}',
        '{"version": 99, "had_previous": true}',
    ])
def test_a_malformed_transaction_record_is_refused(tmp_path, malformed):
    """
    A record this installer cannot read is not one it may act on.

    A future version's record is included: a newer installer may mean
    something different by the same fields, so an older one must not act
    on it.
    """
    config = make_config(tmp_path)
    config.transaction_dir.mkdir(parents = True)
    config.transaction_record.write_text(malformed, encoding = "utf-8")

    with pytest.raises(SystemExit):
        _helpers.reconcile_transaction(config)

    assert config.transaction_record.is_file(), (
        "A record that cannot be read must be preserved for the user.")


def test_a_symlinked_transaction_record_is_refused_and_preserved(tmp_path):
    """
    A transaction record must be a regular file owned by the transaction.

    Following a record symlink could make an unrelated directory look like
    installer state and authorise recursively deleting its contents.
    """
    config = make_config(tmp_path)
    config.transaction_dir.mkdir(parents = True)
    precious = config.transaction_dir / "someone_elses.txt"
    precious.write_text("precious", encoding = "utf-8")

    target = tmp_path / "valid-looking-record.json"
    target.write_text(
        '{"version": 1, "had_previous": true}', encoding = "utf-8")
    config.transaction_record.symlink_to(target)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    assert "no plain record" in str(exc_info.value), (
        "The refusal should identify the missing plain ownership record.")
    assert precious.read_text(encoding = "utf-8") == "precious", (
        "An unowned transaction directory must remain untouched.")
    assert config.transaction_record.is_symlink(), (
        "The record symlink must be preserved.")
    assert target.read_text(encoding = "utf-8").endswith("true}"), (
        "The symlink target must not be touched.")


def test_a_transaction_symlink_is_refused_and_its_target_untouched(tmp_path):
    """
    Recovery must never follow a symlink out of the prefix and delete.

    is_dir follows symlinks, so a link named like the transaction would
    otherwise have its target removed.
    """
    config = make_config(tmp_path)
    config.prefix.mkdir(parents = True, exist_ok = True)

    target = tmp_path / "somewhere_else"
    target.mkdir()
    (target / "precious.txt").write_text("precious", encoding = "utf-8")
    config.transaction_dir.symlink_to(target)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    assert "is a symlink, which this installer never creates" in str(
        exc_info.value), (
        "The message should say a symlink was found, not something else. "
        "The bare word is no good here: this test's own tmp_path contains "
        "it, so any message would match.")
    assert (target / "precious.txt").read_text(encoding = "utf-8") == "precious", (
        "The symlink target must not be touched.")
    assert config.transaction_dir.is_symlink(), (
        "The symlink itself should be left in place.")


@pytest.mark.parametrize(
    "state",
    [
        "first install with backup",
        "previous source missing",
        "previous source unowned",
    ])
def test_a_contradictory_transaction_is_refused_and_preserved(tmp_path, state):
    """
    Recovery must not guess when the record contradicts the filesystem.
    """
    config = make_config(tmp_path)

    if state == "first install with backup":
        _open_transaction(config, had_previous = False)
        config.backup_dir.mkdir(parents = True)
        (config.backup_dir / _helpers.INSTALL_MARKER).touch()
        preserved = config.backup_dir
    elif state == "previous source missing":
        _open_transaction(config, had_previous = True)
        preserved = config.transaction_dir
    else:
        _open_transaction(config, had_previous = True)
        config.src_dir.mkdir(parents = True)
        (config.src_dir / "someone_elses.txt").touch()
        preserved = config.src_dir

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    assert "Nothing has been changed" in str(exc_info.value), (
        "A contradiction should be reported as a fail-closed refusal.")
    assert preserved.exists(), (
        "Contradictory state must be preserved for manual inspection.")
    assert config.transaction_dir.exists(), (
        "A refused transaction must remain available for recovery.")


########################################
# Committed Installs Stay Committed
########################################
def test_a_failed_commit_cleanup_does_not_roll_the_install_back(
        tmp_path,
        monkeypatch):
    """
    Clearing up after a commit is tidying, not part of the transaction.

    The commit is the rename. If removing what is left fails, the install
    is still done, and the next run must not read the remains as rollback
    state and undo it.
    """
    config, _launcher_before = _working_installation(tmp_path)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run())

    real_rmtree = _helpers.shutil.rmtree

    def fail_cleanup(path, *args, **kwargs):
        if Path(path).name.startswith(_helpers.CLEANUP_PREFIX):
            raise OSError("cannot clear up")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(_helpers.shutil, "rmtree", fail_cleanup)

    _helpers.install_sad_source(config, {}, _building_prepare(config))

    assert config.executable.read_text(encoding = "utf-8") == "new gs\n", (
        "The install should have completed.")

    leftovers = list(config.prefix.glob(f"{_helpers.CLEANUP_PREFIX}*"))
    assert leftovers, "This test needs the cleanup to have been left behind."

    # A fresh invocation, with the leftovers still there.
    monkeypatch.setattr(_helpers.shutil, "rmtree", real_rmtree)
    _helpers.reconcile_transaction(config)

    assert config.executable.read_text(encoding = "utf-8") == "new gs\n", (
        "A later run must not read committed leftovers as rollback state.")


########################################
# Interrupted Replacement
########################################
def test_an_interrupted_replacement_before_the_old_tree_moves(tmp_path):
    """
    A run killed before the old tree moved should keep it exactly there.
    """
    config = make_config(tmp_path)
    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    (config.src_dir / "working.txt").write_text("previous", encoding = "utf-8")

    _open_transaction(config, had_previous = True)
    config.staging_dir.mkdir(parents = True)
    (config.staging_dir / "partial.txt").touch()

    _helpers.reconcile_transaction(config)

    assert (config.src_dir / "working.txt").read_text(
        encoding = "utf-8") == "previous", (
        "The untouched tree should stay exactly where it was.")
    assert not config.transaction_dir.exists(), (
        "The partial clone should be discarded.")


########################################
# Ambiguous Recovery State
########################################
@pytest.mark.parametrize("unowned", ["backup", "src"])
def test_recovery_refuses_state_it_cannot_identify_as_its_own(
        tmp_path,
        unowned):
    """
    Recovery must not delete a tree it cannot prove it created.

    Both trees are named so the user can look at them, and neither is
    touched.
    """
    config = make_config(tmp_path)
    _open_transaction(config, had_previous = True)
    config.backup_dir.mkdir(parents = True)
    (config.backup_dir / "backup.txt").touch()
    config.src_dir.mkdir(parents = True)
    (config.src_dir / "src.txt").touch()

    owned = config.src_dir if unowned == "backup" else config.backup_dir
    (owned / _helpers.INSTALL_MARKER).touch()

    with pytest.raises(SystemExit) as exc_info:
        _helpers.reconcile_transaction(config)

    message = str(exc_info.value)

    assert str(config.backup_dir) in message, (
        "The message should name the held-aside tree.")
    assert (config.backup_dir / "backup.txt").is_file(), (
        "An unidentifiable tree must not be removed.")
    assert (config.src_dir / "src.txt").is_file(), (
        "An unidentifiable tree must not be removed.")


########################################
# Rollback That Cannot Complete
########################################
def test_rollback_preserves_transaction_state_it_cannot_validate(tmp_path):
    """
    In-process rollback must fail closed like startup reconciliation.

    Guessing a default for an unreadable record could remove or retire state
    that the installer cannot safely interpret.
    """
    config = make_config(tmp_path)
    _open_transaction(config, had_previous = False)
    config.src_dir.mkdir(parents = True)
    config.marker.touch()
    config.transaction_record.write_text("not json", encoding = "utf-8")

    cause = _helpers.CommandError(["make", "exe"], 2)
    with pytest.raises(_helpers.RollbackError) as exc_info:
        _helpers.rollback(config, cause)

    message = str(exc_info.value)
    assert "transaction state is not safe" in message, (
        "Rollback should report why it refused to infer a state.")
    assert str(config.transaction_dir) in message, (
        "The preserved transaction path should be named exactly.")
    assert config.src_dir.exists(), (
        "Ambiguous source state must not be deleted.")
    assert config.transaction_dir.exists(), (
        "Ambiguous transaction state must not be retired.")


def test_a_rollback_that_cannot_complete_preserves_and_names_the_backup(
        tmp_path,
        monkeypatch):
    """
    A rollback that fails must never lose the only working copy.

    The original failure, the rollback failure, and the preserved path all
    have to reach the user, or they cannot put SAD back themselves.
    """
    config, _launcher_before = _working_installation(tmp_path)

    monkeypatch.setattr(_helpers, "_resolve_branch", lambda config: config.branch)
    monkeypatch.setattr(_helpers, "run", _cloning_run("make exe"))

    def fail_rmtree(path, *args, **kwargs):
        # ignore_errors is honoured, so a rollback that asks for it is not
        # rescued by this stand-in.
        if Path(path) == config.src_dir and not kwargs.get("ignore_errors"):
            raise OSError("cannot remove the failed tree")
        return None

    monkeypatch.setattr(_helpers.shutil, "rmtree", fail_rmtree)

    with pytest.raises(_helpers.RollbackError) as exc_info:
        _helpers.install_sad_source(config, {}, _building_prepare(config))

    message = str(exc_info.value)

    assert str(config.backup_dir) in message, (
        "The preserved backup path should be named exactly.")
    assert "make exe" in message, (
        "The original failure should be reported.")
    assert "cannot remove the failed tree" in message, (
        "The rollback failure should be reported too.")
    assert (config.backup_dir / "bin" / "gs").is_file(), (
        "The only working copy must survive a failed rollback.")


########################################
# In-Place Rebuild
########################################
def test_reuse_clone_builds_in_place_without_cloning_another_tree(
        tmp_path,
        monkeypatch):
    """
    --reuse-clone must rebuild the tree it was pointed at.

    Cloning a second tree would defeat the flag, which exists precisely to
    keep the existing checkout.
    """
    config, _launcher_before = _working_installation(tmp_path)
    config = replace(config, reuse_clone = True)

    monkeypatch.setattr(_helpers, "_check_reuse_matches_request", lambda config: None)

    built_in = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            raise AssertionError("--reuse-clone must not clone another tree")
        built_in.append(kwargs.get("cwd"))
        return None

    monkeypatch.setattr(_helpers, "run", fake_run)

    _helpers.install_sad_source(config, {})

    assert set(built_in) == {config.src_dir}, (
        "--reuse-clone should build in the existing source tree.")
    assert config.executable.read_text(encoding = "utf-8") == "previous gs\n", (
        "An in-place rebuild keeps the tree it was given.")


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
def _install_launcher(config, contents: str = "#!/bin/sh\nexit 0\n") -> None:
    """
    Put an executable file where the launcher would be.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    contents : str, optional
        Script body. Defaults to a script that does nothing.
    """
    config.bin_dir.mkdir(parents = True, exist_ok = True)
    config.launcher.write_text(contents, encoding = "utf-8")
    config.launcher.chmod(0o755)


def test_report_path_setup_is_quiet_when_the_launcher_is_the_one_that_runs(
        tmp_path,
        monkeypatch,
        caplog):
    """
    A launcher that the shell would actually run needs nothing from the user.
    """
    config = make_config(tmp_path)
    _install_launcher(config)

    monkeypatch.setenv("PATH", os.pathsep.join([str(config.bin_dir), "/usr/bin"]))

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    assert "resolves to" in caplog.text, (
        "A reachable launcher should be confirmed as the one that runs.")
    assert "export PATH" not in caplog.text, (
        "No instruction is needed when the launcher already wins.")


########################################
# Launcher Ownership
########################################
def test_write_launcher_refuses_an_unowned_regular_file(tmp_path):
    """
    A sad already on PATH that this installer did not write is not ours.

    Overwriting it would destroy whatever the user or another package
    manager put there.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)
    config.launcher.write_text("#!/bin/sh\necho someone elses sad\n")
    before = config.launcher.read_bytes()

    with pytest.raises(SystemExit) as exc_info:
        _helpers.write_launcher(config)

    assert "not written by this installer" in str(exc_info.value), (
        "The refusal should say why the file was left alone.")
    assert config.launcher.read_bytes() == before, (
        "An unowned launcher must survive byte for byte.")


def test_write_launcher_refuses_a_file_that_merely_mentions_the_marker(
        tmp_path):
    """
    The marker has to be one of the file's own lines.

    Matching it anywhere in the text would let any script that quotes the
    marker, a wrapper or a README fragment, be overwritten.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)
    config.launcher.write_text(
        f'#!/bin/sh\necho "not {_helpers.LAUNCHER_MARKER} really"\n',
        encoding = "utf-8")
    before = config.launcher.read_bytes()

    with pytest.raises(SystemExit):
        _helpers.write_launcher(config)

    assert config.launcher.read_bytes() == before, (
        "A file that only mentions the marker must survive.")


def test_write_launcher_refuses_a_symlink_and_leaves_its_target_alone(tmp_path):
    """
    A symlink must not be followed, or the write lands on its target.

    Writing through a symlink would silently overwrite a file somewhere
    the user never named.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)

    target = tmp_path / "somewhere_else"
    target.write_text("precious\n", encoding = "utf-8")
    config.launcher.symlink_to(target)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.write_launcher(config)

    assert "symlink" in str(exc_info.value), (
        "The refusal should name what was found.")
    assert target.read_text(encoding = "utf-8") == "precious\n", (
        "The symlink target must not be written through.")
    assert config.launcher.is_symlink(), (
        "The symlink itself should be left in place.")


def test_write_launcher_refuses_a_directory(tmp_path):
    """
    A directory at the launcher path is not something to replace.
    """
    config = make_config(tmp_path)
    config.launcher.mkdir(parents = True)

    with pytest.raises(SystemExit) as exc_info:
        _helpers.write_launcher(config)

    assert "not a regular file" in str(exc_info.value), (
        "The refusal should name what was found.")


def test_write_launcher_replaces_a_launcher_it_wrote_itself(tmp_path):
    """
    Reinstalling should upgrade the launcher this installer left behind.
    """
    config = make_config(tmp_path)
    _helpers.write_launcher(config)

    stale = config.launcher.read_text(encoding = "utf-8").replace(
        str(config.src_dir), "/somewhere/stale")
    config.launcher.write_text(stale, encoding = "utf-8")

    _helpers.write_launcher(config)

    contents = config.launcher.read_text(encoding = "utf-8")

    assert _helpers.LAUNCHER_MARKER in contents, (
        "A generated launcher should carry the ownership marker.")
    assert "/somewhere/stale" not in contents, (
        "An owned launcher should be replaced, not kept.")
    assert os.access(config.launcher, os.X_OK), (
        "The replacement should be executable.")


########################################
# Atomic Launcher Write
########################################
def test_a_failed_launcher_write_leaves_no_staging_file(tmp_path, monkeypatch):
    """
    An interrupted write must leave nothing behind on PATH.

    A half-written script in the launcher directory would be picked up by
    the next shell that looked there.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(_helpers.os, "replace", fail_replace)

    with pytest.raises(OSError):
        _helpers.write_launcher(config)

    assert list(config.bin_dir.iterdir()) == [], (
        "No staging file should survive a failed launcher write.")


########################################
# Shadowed Launcher
########################################
def test_report_path_setup_warns_when_another_sad_shadows_the_launcher(
        tmp_path,
        monkeypatch,
        caplog):
    """
    An earlier sad on PATH should be named, not silently accepted.

    The directory being on PATH says nothing about which sad wins, and a
    stale binary earlier in the list would keep running instead.
    """
    config = make_config(tmp_path)
    _install_launcher(config)

    # The legacy location an earlier installer used, and the one most
    # likely to still be sitting ahead of ~/.local/bin.
    legacy = tmp_path / "bin"
    legacy.mkdir()
    shadow = legacy / "sad"
    shadow.write_text("#!/bin/sh\nexit 0\n", encoding = "utf-8")
    shadow.chmod(0o755)

    monkeypatch.setenv(
        "PATH", os.pathsep.join([str(legacy), str(config.bin_dir)]))

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    assert str(shadow) in caplog.text, (
        "The shadowing command should be named so the user can find it.")
    assert str(config.bin_dir) in _printed_export_line(caplog), (
        "The user should be told how to put the new launcher first.")


def test_report_path_setup_warns_when_the_launcher_does_not_resolve(
        tmp_path,
        monkeypatch,
        caplog):
    """
    A launcher directory on PATH with no runnable sad should be reported.
    """
    config = make_config(tmp_path)
    config.bin_dir.mkdir(parents = True)

    monkeypatch.setenv("PATH", str(config.bin_dir))

    with caplog.at_level("INFO", logger = "sad2xs.install_sad._helpers"):
        _helpers.report_path_setup(config)

    assert "does not resolve" in caplog.text, (
        "A directory on PATH with no sad in it should be reported.")


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
