"""
================================================================================
SAD Helpers: Chromaticity
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
import logging
import os
import uuid

import numpy as np

from ._helpers import run_sad, _check_mathematica_output

logger  = logging.getLogger(__name__)

################################################################################
# SAD Survey Print Function
################################################################################
def generate_off_momentum_tune_function():
    """
    TBD
    """

    survey_command  = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Off-Momentum Tune Command
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CalculateOffMomentumTune[x_]:={

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! Set the momentum deviation
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    DP0 = x;

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! Run 4D Twiss Off-Momentum
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    FFS["CALC4D;COD;CALC;"];

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! Get the fractional tunes
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    FractionalPart[Twiss["NX","$$$"]/(2*Pi)],
    FractionalPart[Twiss["NY","$$$"]/(2*Pi)]
};
"""
    return survey_command

################################################################################
# Closed Ring 4D Twiss Function
################################################################################
def chromaticity_sad(
        lattice_filepath:       str,
        line_name:              str,
        dp_extent:              float       = 0.010,
        dp_step:                float       = 0.001,
        compute_higher_orders:  bool | int  = False,
        additional_commands:    str         = "",
        wall_time:              int         = 60,
        sad_path:               str         = "sad"):
    """
    Generate a SAD command to compute the chromaticity parameters of a lattice.
    """

    logger.debug("Creating SAD command")

    ########################################
    # SAD changes cwd to the directory of
    # the input script, so the script must
    # live in cwd (same dir as the lattice).
    # Use uuid names to avoid collisions;
    # try/finally ensures cleanup.
    ########################################
    uid      = uuid.uuid4().hex[:12]
    cmd_file = f"_sad_chrom_{uid}.sad"
    out_file = f"_sad_chrom_{uid}.dat"

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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Run any additional altering commands
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{additional_commands};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Twiss to get survey data
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CELL;
COD;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Include the off momentum tune function
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{generate_off_momentum_tune_function()}

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Scan chromaticity and write directly to file (dp qx qy per row)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
fn = OpenWrite["{out_file}"];
$FORM="12.10";
Table[
    tunes = CalculateOffMomentumTune[x];
    WriteString[fn, x, " ", tunes[1], " ", tunes[2], "\\n"],
    {{x, -{dp_extent}, {dp_extent}, {dp_step} }}
];
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
            task_name   = "chromaticity",
            wall_time   = wall_time,
            sad_path    = sad_path)

        with open(out_file, encoding="utf-8") as _f:
            _raw = _f.read()
        _check_mathematica_output(_raw)

        chrom_scan = np.loadtxt(out_file, ndmin = 2)

    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

    ########################################
    # Data evaluation
    ########################################
    dp  = chrom_scan[:, 0]
    qx  = chrom_scan[:, 1]
    qy  = chrom_scan[:, 2]

    ########################################
    # Linear Chromaticities
    ########################################
    linear_dqx  = np.flip(np.polyfit(dp, qx, 1))[1]
    linear_dqy  = np.flip(np.polyfit(dp, qy, 1))[1]

    ########################################
    # Higher Order Chromaticities
    ########################################
    if compute_higher_orders is True:
        compute_higher_orders = 3

    higher_coeffs_x    = None
    higher_coeffs_y    = None
    if compute_higher_orders:
        higher_coeffs_x    = np.flip(np.polyfit(dp, qx, compute_higher_orders))
        higher_coeffs_y    = np.flip(np.polyfit(dp, qy, compute_higher_orders))

    ########################################
    # Output dictionary
    ########################################
    chrom_scan = {
        "dp":               dp,
        "qx":               qx,
        "qy":               qy,
        "dqx_linear":       linear_dqx,
        "dqy_linear":       linear_dqy,
        "higher_order_qx":  higher_coeffs_x,
        "higher_order_qy":  higher_coeffs_y}

    return chrom_scan
