"""
================================================================================
SAD Helpers: Transfer Matrix
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-20
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import ast
import logging
import os
import uuid

import numpy as np

from ._helpers import run_sad, _check_mathematica_output

logger  = logging.getLogger(__name__)

################################################################################
# Calculate Transfer Matrix
################################################################################
def transfer_matrix_sad(
        lattice_filepath:       str,
        line_name:              str,
        start_element:          str | None  = None,
        end_element:            str | None  = None,
        wall_time:              int         = 30,
        sad_path:               str         = "sad") -> np.ndarray:
    """
    Compute the transfer matrix of a SAD lattice between two elements.

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file.
    line_name : str
        Name of the beamline in the SAD lattice.
    start_element : str | None, optional
        Name of the starting element for the transfer matrix calculation.
        If None, the start of the beamline is used.
    end_element : str | None, optional
        Name of the ending element for the transfer matrix calculation.
        If None, the end of the beamline is used.
    wall_time : int, optional
        Timeout, in seconds, for the SAD subprocess. Defaults to 30.
    sad_path : str, optional
        Path to the SAD executable. Defaults to "sad".

    Returns
    -------
    np.ndarray
        The transfer matrix as a NumPy array.

    Raises
    ------
    ValueError
        If exactly one of `start_element`/`end_element` is given (both
        or neither are required), if SAD's output contains a
        Mathematica undefined-symbol marker (see
        `_check_mathematica_output`), or if no matrix is found in
        SAD's output.
    RuntimeError
        If the SAD subprocess times out or exits non-zero (see
        `run_sad`).
    """

    ########################################
    # Ensure both or neither of start_element and end_element are provided
    ########################################
    if start_element is not None and end_element is None:
        raise ValueError("If start_element is provided, end_element must also be provided")
    if start_element is None and end_element is not None:
        raise ValueError("If end_element is provided, start_element must also be provided")

    logger.debug("Creating SAD command")

    ########################################
    # SAD changes cwd to the directory of
    # the input script, so the script must
    # live in cwd (same dir as the lattice).
    # Use uuid names to avoid collisions;
    # try/finally ensures cleanup.
    ########################################
    uid      = uuid.uuid4().hex[:12]
    cmd_file = f"_sad_tmatrix_{uid}.sad"
    out_file = f"_sad_tmatrix_{uid}.dat"

    if start_element is not None and end_element is not None:
        sad_command = f"""OFF ECHO;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Start FFS
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
FFS;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Load and set line
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
GetMAIN["./{lattice_filepath}"];
USE {line_name};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 4D Transfer Matrix Calculation
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CALC4D;
CALC;
TM = TransferMatrix["{start_element}", "{end_element}"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Write matrix to file in SAD native format
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
fn = OpenWrite["{out_file}"];
WriteString[fn, TM];
Close[fn];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""
    else:
        sad_command = f"""OFF ECHO;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Start FFS
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
FFS;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Load and set line
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
GetMAIN["./{lattice_filepath}"];
USE {line_name};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 4D Transfer Matrix Calculation
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CALC4D;
CALC;
TM = TransferMatrix[1, -1];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Write matrix to file in SAD native format
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
fn = OpenWrite["{out_file}"];
WriteString[fn, TM];
Close[fn];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    try:
        run_sad(
            sad_command = sad_command,
            cmd_file    = cmd_file,
            task_name   = "transfer matrix",
            wall_time   = wall_time,
            sad_path    = sad_path)

        with open(out_file, "r", encoding = "utf-8") as f:
            raw = f.read()
        _check_mathematica_output(raw)

        start = raw.find("{{")
        end   = raw.rfind("}}")
        if start == -1 or end == -1:
            raise ValueError("Matrix not found in output file")
        matrix_str  = raw[start:end + 2]
        cleaned     = matrix_str.replace("}", "]").replace("{", "[")
        matrix_list = ast.literal_eval(cleaned)
        rmatrix     = np.array(matrix_list, dtype = float)

    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

    return rmatrix
