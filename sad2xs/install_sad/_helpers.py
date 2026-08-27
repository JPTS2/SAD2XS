"""
================================================================================
SAD Installation Shared Helpers
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
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

logger  = logging.getLogger(__name__)

################################################################################
# Default Locations
################################################################################
SAD_GIT_REPO_URL    = "https://github.com/KatsOide/SAD.git"
SAD_GIT_BRANCH      = "master"

# git ls-remote --exit-code: the remote answered, and has no such head.
NO_MATCHING_REF     = 2

# Written inside the source tree, and only once a clone has succeeded, so it
# marks exactly the directory this installer created. A marker in the parent
# prefix would outlive its own tree and authorise deleting whatever replaced it.
INSTALL_MARKER      = ".sad2xs-install"


def default_prefix() -> Path:
    """
    Return the default directory for the SAD source tree and build logs.

    Returns
    -------
    Path
        The XDG data directory for this package.
    """
    return (Path.home() / ".local" / "share" / "sad2xs").resolve()


def default_bin_dir() -> Path:
    """
    Return the default directory for the `sad` launcher.

    Debian and RHEL family profiles put `~/.local/bin` on PATH once it
    exists, so the launcher lands somewhere the shell already looks.

    Returns
    -------
    Path
        The XDG user binary directory.
    """
    return (Path.home() / ".local" / "bin").resolve()

################################################################################
# Install Configuration
################################################################################
@dataclass(frozen = True)
class InstallConfig:
    """
    Where SAD is built and installed, and which source is used.

    Parameters
    ----------
    prefix : Path
        Directory holding the SAD source tree and the build logs.
    bin_dir : Path
        Directory the `sad` launcher is written to.
    repo_url : str
        Git URL to clone SAD from.
    branch : str
        Branch to clone.
    branch_explicit : bool
        Whether `branch` came from the user rather than the default. An
        absent default branch falls back to the remote's own default; an
        absent explicit one is an error.
    reuse_clone : bool
        If True, keep an existing source tree instead of replacing it.
    """
    prefix:             Path
    bin_dir:            Path
    repo_url:           str
    branch:             str
    branch_explicit:    bool
    reuse_clone:        bool

    def __post_init__(self) -> None:
        """
        Normalise both directories to absolute, symlink-free paths.

        `write_launcher` bakes `src_dir` into a script that runs from any
        directory, so a relative path would produce a launcher that only
        works from the directory it was installed from.
        """
        object.__setattr__(self, "prefix",  self.prefix.expanduser().resolve())
        object.__setattr__(self, "bin_dir", self.bin_dir.expanduser().resolve())

    @property
    def src_dir(self) -> Path:
        """Path: SAD source tree."""
        return self.prefix / "src"

    @property
    def log_dir(self) -> Path:
        """Path: Directory holding the build logs."""
        return self.prefix / "logs"

    @property
    def build_log(self) -> Path:
        """Path: Log file the build output is teed to."""
        return self.log_dir / "build.log"

    @property
    def marker(self) -> Path:
        """Path: Marker identifying the source tree as this installer's."""
        return self.src_dir / INSTALL_MARKER

    @property
    def launcher(self) -> Path:
        """Path: The `sad` launcher script."""
        return self.bin_dir / "sad"

    @property
    def executable(self) -> Path:
        """Path: The SAD binary produced by the build."""
        return self.src_dir / "bin" / "gs"

################################################################################
# Command Error
################################################################################
class CommandError(RuntimeError):
    """
    Raised when a subprocess returns non-zero.

    Parameters
    ----------
    cmd : Iterable[str]
        Command that was run.
    returncode : int
        Return code from the command.
    log_path : Path, optional
        Path to the log file the command wrote to. Defaults to None.
    """
    def __init__(
            self,
            cmd:        Iterable[str],
            returncode: int,
            log_path:   Path | None = None) -> None:
        """
        Record the failed command, its exit status, and any log file.
        """
        self.cmd        = list(cmd)
        self.returncode = returncode
        self.log_path   = log_path

        msg = f"""Command failed ({returncode}): {" ".join(self.cmd)}"""
        if log_path:
            msg += f"\nLog: {log_path}"
        super().__init__(msg)

################################################################################
# Command Runner
################################################################################

########################################
# Log Tail Reporting
########################################
def _log_tail(log_path: Path, n_lines: int = 120) -> None:
    """
    Log the last lines of a build log, best-effort.

    Called on build failure, where the cause is usually near the end of a
    log far too long to show whole.

    Parameters
    ----------
    log_path : Path
        Path to the log file.
    n_lines : int, optional
        Number of lines to show from the end of the log. Defaults to 120.
    """
    try:
        lines   = log_path.read_text(errors = "replace").splitlines()
    except OSError as error:
        logger.info(f"(could not read log) {log_path}: {error}")
        return

    tail    = lines[-n_lines:]
    logger.info("\n" + "#" * 80)
    logger.info(f"Last {len(tail)} lines of log: {log_path}")
    logger.info("#" * 80)
    for line in tail:
        logger.info(line)
    logger.info("#" * 80 + "\n")

########################################
# Run Shell Commands
########################################
def run(
        cmd:            list[str],
        cwd:            Path | str | None       = None,
        env:            dict[str, str] | None   = None,
        check:          bool                    = True,
        log_path:       Path | None             = None,
        stdin_devnull:  bool                    = False) -> subprocess.CompletedProcess | int:
    """
    Run a shell command.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments to run.
    cwd : Path or str, optional
        Working directory to run the command in. Defaults to None.
    env : dict, optional
        Environment variables to use. Defaults to None.
    check : bool, optional
        If True, raise CommandError on a non-zero return code. Defaults to
        True.
    log_path : Path, optional
        If given, tee stdout/stderr to this file. Defaults to None.
    stdin_devnull : bool, optional
        If True, set stdin to /dev/null. Defaults to False.

    Returns
    -------
    subprocess.CompletedProcess or int
        The completed process, or the return code when `log_path` is given.

    Raises
    ------
    CommandError
        If `check` is True and the command returns non-zero.
    """
    logger.info(f"""▶ Running: {" ".join(cmd)}""")
    if cwd:
        logger.info(f"  cwd: {cwd}")

    stdin = subprocess.DEVNULL if stdin_devnull else None

    if log_path is None:
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            cmd,
            cwd     = str(cwd) if cwd else None,
            env     = env,
            stdin   = stdin)
        if check and process.returncode != 0:
            raise CommandError(cmd, process.returncode)

        return process

    log_path.parent.mkdir(parents = True, exist_ok = True)
    with log_path.open("a") as log_file:
        log_file.write(f"""\n\n$ {" ".join(cmd)}\n""")
        log_file.flush()

        # errors="replace": a compiler in a non-UTF-8 locale would otherwise
        # kill the build with a UnicodeDecodeError over a cosmetic byte.
        with subprocess.Popen(
                cmd,
                cwd     = str(cwd) if cwd else None,
                env     = env,
                text    = True,
                errors  = "replace",
                stdout  = subprocess.PIPE,
                stderr  = subprocess.STDOUT,
                stdin   = stdin,
                bufsize = 1) as process:

            # The build's own output, passed through verbatim rather than
            # logged, and flushed so it stays ordered against the logger's
            # stderr when either is redirected.
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log_file.write(line)
            returncode = process.wait()

    if check and returncode != 0:
        _log_tail(log_path)
        raise CommandError(cmd, returncode, log_path = log_path)
    return returncode

################################################################################
# Source Tree
################################################################################

########################################
# Checkout Inspection
########################################
def _git_value(src_dir: Path, *args: str) -> str | None:
    """
    Read one value out of a git checkout, or None if it cannot be read.

    Parameters
    ----------
    src_dir : Path
        Directory to inspect.
    *args : str
        Arguments following `git -C <src_dir>`.

    Returns
    -------
    str or None
        The trimmed output, or None if the directory is not a checkout or
        git reported an error.
    """
    if not (src_dir / ".git").is_dir():
        return None

    process = subprocess.run(           # pylint: disable=subprocess-run-check
        ["git", "-C", str(src_dir), *args],
        text    = True,
        stdout  = subprocess.PIPE,
        stderr  = subprocess.DEVNULL)
    if process.returncode != 0:
        return None
    return process.stdout.strip()


def _installer_owns_tree(config: InstallConfig) -> bool:
    """
    Return True if the existing source tree is this installer's to replace.

    The marker is the only proof accepted. A matching git origin is not
    enough: a user's own SAD checkout would then be deleted by a reinstall
    that happened to point at the same directory.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Returns
    -------
    bool
        True if the tree may be removed.
    """
    return config.marker.is_file()

########################################
# Prefix Guard
########################################
def _guard_prefix(config: InstallConfig) -> None:
    """
    Refuse a prefix that cannot be safely written to.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Raises
    ------
    SystemExit
        If the prefix is the user's home directory or a filesystem root.
    """
    # Both sides resolved: where home is reached through a symlink, as on
    # AFS, comparing a resolved prefix to an unresolved home fails open.
    resolved = config.prefix
    if resolved == Path.home().resolve() or resolved == resolved.parent:
        sys.exit(
            f"Refusing to install into {resolved}. Choose a dedicated "
            f"directory, such as {default_prefix()}.")

########################################
# Source Selection
########################################
def _resolve_branch(config: InstallConfig) -> str | None:
    """
    Return the branch to clone, or None to take the remote's default.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Returns
    -------
    str or None
        The branch name, or None when the remote default should be used.

    Raises
    ------
    SystemExit
        If a branch the user asked for by name is absent on the remote. A
        typo would otherwise install unintended source and report success.
    """
    try:
        process = subprocess.run(       # pylint: disable=subprocess-run-check
            ["git", "ls-remote", "--exit-code", "--heads",
             config.repo_url, config.branch],
            text    = True,
            stdout  = subprocess.DEVNULL,
            stderr  = subprocess.PIPE)
    except OSError as error:
        sys.exit(f"Could not run git to query {config.repo_url}: {error}")

    if process.returncode == 0:
        return config.branch

    # git ls-remote --exit-code returns 2 for "queried fine, no such head".
    # Anything else is the remote or the network failing, which must not be
    # reported as a missing branch.
    if process.returncode != NO_MATCHING_REF:
        sys.exit(
            f"Could not query {config.repo_url} for branch "
            f"{config.branch!r} (git exit {process.returncode}).\n"
            f"{process.stderr.strip()}")

    if config.branch_explicit:
        sys.exit(
            f"Branch {config.branch!r} does not exist on {config.repo_url}. "
            f"Check the name, or omit --branch to use the remote default.")

    # The default branch name only: upstream renaming it must not break
    # every install, so defer to whatever the remote calls its default.
    logger.warning(
        f"Branch {config.branch!r} not found on the remote; "
        f"using the remote default branch instead.")
    return None


def _check_reuse_matches_request(config: InstallConfig) -> None:
    """
    Reject reuse of a checkout that is not the requested source.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Raises
    ------
    SystemExit
        If the existing checkout's origin or branch differs from what was
        asked for, which would otherwise build source the user did not
        request while appearing to honour the arguments.
    """
    # Fails closed: an unreadable origin, an empty .git, or a git that will
    # not run all return None, and none of them prove the tree is the source
    # that was asked for.
    origin = _git_value(config.src_dir, "remote", "get-url", "origin")
    if origin != config.repo_url:
        found = origin if origin is not None else "unreadable"
        sys.exit(
            f"{config.src_dir} has origin {found}, not {config.repo_url}. "
            f"Drop --reuse-clone to replace it, or choose another --prefix.")

    if not config.branch_explicit:
        return

    # A detached HEAD reports "HEAD", which is never a branch name a user
    # asked for, so it is refused along with the unreadable cases.
    branch = _git_value(config.src_dir, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != config.branch:
        found = branch if branch is not None else "unreadable"
        sys.exit(
            f"{config.src_dir} is on branch {found}, not {config.branch!r}. "
            f"Drop --reuse-clone to re-clone it, or check out the branch "
            f"yourself.")

########################################
# Clone SAD
########################################
def clone_sad(config: InstallConfig) -> bool:
    """
    Put a SAD source tree at the configured location.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Returns
    -------
    bool
        True if an existing source tree was reused. Once a clone has run,
        nothing about the tree distinguishes the two cases, so the answer
        has to come from here rather than be re-derived later.

    Raises
    ------
    SystemExit
        If the prefix is unsafe, if an existing tree is not this
        installer's to replace, or if the requested source cannot be had.
    CommandError
        If the clone returns non-zero. The previous source tree is left
        untouched in that case.
    """
    _guard_prefix(config)

    config.log_dir.mkdir(parents = True, exist_ok = True)

    # Truncated so a failure tail cannot be read from an earlier run. Ahead of
    # the reuse branch, which would otherwise keep appending across rebuilds.
    config.build_log.write_text("")
    logger.info(f"Build log: {config.build_log}")

    if config.reuse_clone and (config.src_dir / ".git").is_dir():
        _check_reuse_matches_request(config)
        logger.info(f"Reusing existing source tree: {config.src_dir}")
        return True

    # Everything that can refuse the install runs before anything is removed:
    # a mistyped branch must not cost the user a working installation.
    branch = _resolve_branch(config)
    if config.src_dir.exists() and not _installer_owns_tree(config):
        sys.exit(
            f"{config.src_dir} already exists and was not created by this "
            f"installer. Remove it yourself, or choose another --prefix.")

    cmd = ["git", "clone", "--depth", "1"]
    if branch is not None:
        cmd += ["--branch", branch]

    # Clone into a sibling of src on the same filesystem and swap it in only
    # once it is complete, so a failed or interrupted clone leaves the
    # previous installation exactly as it was.
    staging = Path(tempfile.mkdtemp(dir = config.prefix, prefix = ".src-staging-"))
    try:
        run(
            cmd + [config.repo_url, str(staging)],
            log_path        = config.build_log,
            stdin_devnull   = True)
        (staging / INSTALL_MARKER).touch()
    except BaseException:
        shutil.rmtree(staging, ignore_errors = True)
        raise

    if config.src_dir.exists():
        logger.info(f"Replacing previous source tree: {config.src_dir}")
        shutil.rmtree(config.src_dir)
    staging.rename(config.src_dir)
    return False

################################################################################
# Build
################################################################################

########################################
# Make SAD
########################################
def make_sad(
        config:         InstallConfig,
        env:            dict[str, str],
        reused_tree:    bool) -> None:
    """
    Run SAD's build steps against a prepared environment.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    env : dict
        Environment variables for the build.
    reused_tree : bool
        Whether `clone_sad` reused an existing tree, as it returns.

    Raises
    ------
    CommandError
        If a build step returns non-zero.
    """
    # Only meaningful on a reused tree; a fresh clone has nothing to clean,
    # and upstream's clean target returns non-zero when there is not.
    if reused_tree:
        run(
            ["make", "clean"],
            cwd             = config.src_dir,
            env             = env,
            log_path        = config.build_log,
            stdin_devnull   = True,
            check           = False)

    for target in ("depend", "exe"):
        run(
            ["make", target],
            cwd             = config.src_dir,
            env             = env,
            log_path        = config.build_log,
            stdin_devnull   = True)

########################################
# Verify Executable
########################################
def verify_executable(config: InstallConfig) -> None:
    """
    Check that the build produced a runnable SAD binary.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Raises
    ------
    SystemExit
        If the binary is missing or not executable.
    """
    if not os.access(config.executable, os.X_OK):
        sys.exit(
            f"Build finished but {config.executable} is missing or not "
            f"executable. See {config.build_log}")
    logger.info(f"Build OK: {config.executable}")

################################################################################
# Launcher
################################################################################
def write_launcher(config: InstallConfig) -> None:
    """
    Write the `sad` launcher script.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.

    Notes
    -----
    1) Called with a file, the launcher runs in batch mode from the caller's
       working directory
    2) Called with no arguments, it runs interactively from the source
       directory, which is where SAD looks for its own support files
    """
    config.bin_dir.mkdir(parents = True, exist_ok = True)

    # shlex.quote: the prefix is user-supplied and lands inside shell source,
    # where a quote or $( ) would break the script or be evaluated.
    src_dir = shlex.quote(str(config.src_dir))

    # python3 rather than realpath(1), which older macOS does not ship.
    config.launcher.write_text(f"""#!/usr/bin/env bash
set -e
SAD_DIR={src_dir}
GS_EXEC="$SAD_DIR/bin/gs"
CALL_DIR="$(pwd)"

if [[ $# -gt 0 ]]; then
    if [[ "$1" = /* ]]; then
        SAD_INPUT="$1"
    else
        SAD_INPUT="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$CALL_DIR/$1")"
    fi
    shift
    cd "$CALL_DIR" || exit 1
    exec "$GS_EXEC" "$SAD_INPUT" "$@"
else
    cd "$SAD_DIR" || exit 1
    exec "$GS_EXEC"
fi
""")
    config.launcher.chmod(0o755)
    logger.info(f"Launcher written: {config.launcher}")

################################################################################
# PATH Reporting
################################################################################
def report_path_setup(config: InstallConfig) -> None:
    """
    Report whether the launcher directory is reachable from the shell.

    Shell configuration is never modified. Editing a user's rc file is
    invasive, and a throwaway `--bin-dir` would leave a permanent entry
    behind pointing at a directory that need not outlive the shell.

    Parameters
    ----------
    config : InstallConfig
        Install configuration.
    """
    bin_dir = str(config.bin_dir)
    if bin_dir in os.environ.get("PATH", "").split(os.pathsep):
        logger.info(f"{bin_dir} is already on PATH")
        return

    logger.warning(f"{bin_dir} is not on PATH")
    # Quoted because this line is meant to be pasted into a shell, and the
    # directory came from --bin-dir.
    logger.info(
        f"Add it by appending this line to your shell configuration:\n"
        f'  export PATH={shlex.quote(bin_dir)}:"$PATH"')
