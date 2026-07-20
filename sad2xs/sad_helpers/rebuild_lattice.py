"""
================================================================================
SAD Helpers: Rebuild Lattice
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
import uuid

from ._helpers import run_sad, _check_mathematica_output

logger  = logging.getLogger(__name__)

################################################################################
# Rebuild SAD lattice
################################################################################
def rebuild_sad_lattice(
        lattice_filepath:       str,
        line_name:              str,
        output_filepath:        str | None  = None,
        additional_commands:    str         = "",
        wall_time:              int         = 30,
        sad_path:               str         = "sad"):
    """
    Output a rebuilt SAD lattice file after modifications.

    Parameters
    ----------
    lattice_filepath : str
        Path to the input SAD lattice file.
    line_name : str
        Name of the line in the SAD lattice file.
    additional_commands : str, optional
        Additional SAD commands to include before saving the lattice.
    output_filepath : str or None, optional
        Path to the output SAD lattice file. If None, appends "_rebuilt" to the
        input filename.
    """

    ########################################
    # Check for output filename
    ########################################
    if output_filepath is None:
        output_filepath = lattice_filepath.replace(".sad", "_rebuilt.sad")

    ########################################
    # Generate the twiss command
    ########################################
    uid      = uuid.uuid4().hex[:12]
    cmd_file = f"_sad_rebuild_{uid}.sad"

    logger.debug("Creating SAD command")
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
! Compute 4D Transfer Line Twiss
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
INS;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Write out rebuilt lattice
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
of  = OpenWrite["./{output_filepath}"];
WriteString[of, "MOMENTUM = "//MOMENTUM//";\\n"];
WriteString[of, "MASS = "//MASS//";\\n"];
WriteString[of, "CHARGE = "//CHARGE//";\\n"];
WriteString[of, "FSHIFT = "//FSHIFT//";\\n"];
FFS["output "//of//" type"];
WriteBeamLine[of, ExtractBeamLine[], Format->"MAIN", Name->{{"{line_name}"}}];
Close[of];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    run_sad(
        sad_command = sad_command,
        cmd_file    = cmd_file,
        task_name   = "rebuild",
        wall_time   = wall_time,
        sad_path    = sad_path)

    ########################################
    # Guard against degenerate SAD output in the rebuilt lattice
    ########################################
    with open(output_filepath, encoding = "utf-8") as f:
        _check_mathematica_output(f.read())
