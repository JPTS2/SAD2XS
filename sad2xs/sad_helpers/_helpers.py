"""
(Unofficial) SAD to XSuite Converter: SAD Helpers Internal Utilities
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-04
"""

################################################################################
# Required Packages
################################################################################
import logging
import os
import subprocess

logger  = logging.getLogger(__name__)

################################################################################
# SAD Subprocess Runner
################################################################################
def run_sad(
        sad_command:    str,
        cmd_file:       str,
        task_name:      str,
        wall_time:      int,
        sad_path:       str) -> str:
    """
    Write a SAD command file, run SAD on it, and return SAD's terminal output.

    The command file is removed afterwards regardless of outcome. Failures
    are raised as RuntimeError with SAD's stdout/stderr embedded, so the
    diagnostic travels with the exception instead of relying on terminal
    scrollback.
    """
    logger.debug(f"Running SAD {task_name} ({cmd_file})")
    try:
        with open(cmd_file, "w", encoding = "utf-8") as f:
            f.write(sad_command)

        try:
            process = subprocess.run(
                [sad_path, cmd_file],
                capture_output  = True,
                text            = True,
                timeout         = wall_time,
                check           = True)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"SAD {task_name} timed out after {wall_time}s") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"SAD {task_name} exited with non-zero status "
                f"{exc.returncode}.\n"
                f"--- SAD stdout ---\n{exc.stdout}\n"
                f"--- SAD stderr ---\n{exc.stderr}") from exc

    finally:
        if os.path.exists(cmd_file):
            os.remove(cmd_file)

    logger.debug(f"SAD {task_name} terminal output:\n{process.stdout}")
    return process.stdout

################################################################################
# Mathematica Output Guard
################################################################################
_MATHEMATICA_UNDEFINED = frozenset({
    "medium",
    "$DefaultFontWeight",
    "Indeterminate",
    "ComplexInfinity",
    "DirectedInfinity"})

def _check_mathematica_output(raw: str) -> None:
    found = [s for s in _MATHEMATICA_UNDEFINED if s in raw]
    if found:
        raise ValueError(
            f"SAD output contains Mathematica undefined symbols {found}. "
            f"The lattice configuration is physically degenerate "
            f"(SAD exited 0 but the computation failed). "
            f"Run with sad2xs.set_log_level('debug') to see the full SAD "
            f"terminal output.")
