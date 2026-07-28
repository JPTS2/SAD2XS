"""
================================================================================
SAD Helpers: Survey
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-28
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import logging
import os
import uuid

import numpy as np
import tfs
import xtrack as xt

from ._helpers import run_sad, _check_mathematica_output

logger  = logging.getLogger(__name__)

################################################################################
# SAD Survey Print Function
################################################################################
def generate_survey_print_function() -> str:
    """
    Build the SAD-side `SaveSurveyFile[filename_]` function
    definition.

    Writes every line element's TFS-style survey record (NAME, TYPE,
    S, L, GX, GY, GZ, GCHI1, GCHI2, GCHI3) to `filename`. Used by
    `survey_sad` to extract SAD's global survey coordinates.

    Returns
    -------
    str
        The SAD command text defining `SaveSurveyFile`.
    """

    survey_command  = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Survey Command
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SaveSurveyFile[filename_]:=Module[
    {fn, pos},
    fn  = OpenWrite[filename];

    $FORM="12.10";
    
    WriteString[fn, "@ ",
        StringFill["TIME"," ", 20],
        "%s ",
        "\\"",
        StringFill[DateString[]," ",-20],
        "\\"",
        "\\n"];

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! Initialise Survey File
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    WriteString[fn, "* ",
        StringFill["NAME"," ", 20]," ",
        StringFill["TYPE"," ", -12],"    ",
        StringFill["S"," ", -12],"    ",
        StringFill["L"," ", -12],"    ",
        StringFill["GX"," ", -12],"    ",
        StringFill["GY"," ", -12],"    ",
        StringFill["GZ"," ", -12],"    ",
        StringFill["GCHI1"," ", -12],"    ",
        StringFill["GCHI2"," ", -12],"    ",
        StringFill["GCHI3"," ", -12],"    ",
        "\\n"];
    
    WriteString[fn, "$ ",
        StringFill["%s"," ", 20]," ",
        StringFill["%s"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        "\\n"];
    
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ! Get element positions
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    pos=LINE["POSITION","*{^$$$}"];
    Do[
        WriteString[fn,     " ",
            StringFill[StringJoin["\\"",LINE["NAME",pos[i]],"\\""]," ", 21]," ",
            StringFill[StringJoin["\\"",LINE["TYPENAME",pos[i]],"\\""]," ", -12],"    ",
            LINE["LENG",pos[i]],"    ",
            LINE["L",pos[i]],"    ",
            LINE["GX",pos[i]],"    ",
            LINE["GY",pos[i]],"    ",
            LINE["GZ",pos[i]],"    ",
            LINE["GCHI1",pos[i]],"    ",
            LINE["GCHI2",pos[i]],"    ",
            LINE["GCHI3",pos[i]],"    ",
            "\\n"
        ]
        ,{i, Length[pos]}
        ];
    Close[fn];
];
"""
    return survey_command

################################################################################
# Closed Ring 4D Twiss Function
################################################################################
def survey_sad(
        lattice_filepath:           str,
        line_name:                  str,
        closed:                     bool    = True,
        reverse_element_order:      bool    = False,
        reverse_survey_horizontal:  bool    = False,
        reverse_survey_vertical:    bool    = False,
        additional_commands:        str     = "",
        wall_time:                  int     = 30,
        sad_path:                   str     = "sad") -> xt.survey.SurveyTable:
    """
    Compute a lattice's global survey coordinates in real SAD, as an
    Xsuite SurveyTable.

    Runs SAD's own survey (CELL/INS + COD + CALC), reads back the TFS
    file `generate_survey_print_function` writes, maps SAD element
    TYPE strings onto their Xsuite equivalents, and reassembles the
    result as an `xt.survey.SurveyTable` with axes remapped into
    Xsuite's convention (X = -GY, Y = -GZ, Z = +GX; theta = -GCHI1,
    phi = -GCHI2, psi = +GCHI3). `reverse_element_order` uses SAD's
    own `-ExtractBeamLine[]` to reverse natively rather than
    reimplementing reversal in Python (see docs/reference/sad-behaviour.md).

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file, relative to the current working
        directory (SAD changes into the script's own directory, so
        the lattice must be reachable from there).
    line_name : str
        The SAD line to USE.
    closed : bool, optional
        If True, treat the lattice as a closed ring (SAD's CELL); if
        False, as a transfer line (SAD's INS). Defaults to True.
    reverse_element_order : bool, optional
        Reverse the line's element order natively in SAD before
        surveying. Defaults to False.
    reverse_survey_horizontal : bool, optional
        Flip the sign of X/theta/psi in the returned survey (mirrors
        `reverse_line_survey_horizontal`'s convention). Defaults to
        False.
    reverse_survey_vertical : bool, optional
        Flip the sign of Y/phi/psi in the returned survey (mirrors
        `reverse_line_survey_vertical`'s convention). Defaults to
        False.
    additional_commands : str, optional
        Extra SAD commands run after loading the line and before the
        survey. Defaults to "".
    wall_time : int, optional
        Timeout, in seconds, for the SAD subprocess. Defaults to 30.
    sad_path : str, optional
        Path to the SAD executable. Defaults to "sad".

    Returns
    -------
    xt.survey.SurveyTable
        The lattice's global survey coordinates, in Xsuite's axis
        convention, ordered by S. Element types not in the SAD-to-
        Xsuite map are labelled "Unknown".

    Raises
    ------
    RuntimeError
        If the SAD subprocess times out or exits non-zero (see
        `run_sad`).
    ValueError
        If SAD's output contains a Mathematica undefined-symbol
        marker (see `_check_mathematica_output`).
    """

    ########################################
    # Configure Settings
    ########################################
    closed_flag = "CELL;" if closed else "INS;"

    ########################################
    # Generate the twiss command
    ########################################
    uid      = uuid.uuid4().hex[:12]
    cmd_file = f"_sad_survey_{uid}.sad"
    out_file = f"_sad_survey_{uid}.tfs"

    # Native SAD reversal via a live ExtractBeamLine[] -- see docs/reference/sad-behaviour.md.
    reversal_commands = ""
    if reverse_element_order:
        use_line_name = f"REV{uid.upper()}"
        reversal_commands = (
            f"LINE {use_line_name} = -ExtractBeamLine[];\n"
            f"USE {use_line_name};\n")

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
{reversal_commands}

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Run any additional altering commands
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{additional_commands};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Twiss to get survey data
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{closed_flag}
COD;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Include the survey print function
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{generate_survey_print_function()}
SaveSurveyFile["./{out_file}"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    try:
        run_sad(
            sad_command = sad_command,
            cmd_file    = cmd_file,
            task_name   = "survey",
            wall_time   = wall_time,
            sad_path    = sad_path)

        with open(out_file, encoding="utf-8") as _f:
            _raw = _f.read()
        _check_mathematica_output(_raw)

        sad_survey = tfs.read(out_file)

    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

    ########################################
    # Convert the element types
    ########################################
    element_equiv_map = {
        "DRIFT":        "Drift",
        "BEND":         "Bend",
        "QUAD":         "Quadrupole",
        "SEXT":         "Sextupole",
        "OCT":          "Octupole",
        "MULT":         "Multipole",
        "SOL":          "Solenoid",
        "CAVI":         "Cavity",
        "APERT":        "LimitEllipse",
        "COORD":        "Translation",
        "MARK":         "Marker",
        "MONI":         "Marker",
        "BEAMBEAM":     "Marker"}

    element_types   = []
    for etype in sad_survey["TYPE"]:                         # type: ignore
        if etype in element_equiv_map:
            element_types.append(element_equiv_map[etype])
        else:
            element_types.append("Unknown")
    sad_survey["TYPE"] = element_types

    ########################################
    # Convert to TwissTable
    ########################################
    s_idx       = np.argsort(np.array(sad_survey["S"]), kind = "stable")
    sv_sad      = xt.survey.SurveyTable({                       # type: ignore
        "s":            +1 * np.array(sad_survey["S"])[s_idx],
        "l":            +1 * np.array(sad_survey["L"])[s_idx],
        "X":            -1 * np.array(sad_survey["GY"])[s_idx],
        "Y":            -1 * np.array(sad_survey["GZ"])[s_idx],
        "Z":            +1 * np.array(sad_survey["GX"])[s_idx],
        "theta":        -1 * np.unwrap(np.array(sad_survey["GCHI1"]))[s_idx],
        "phi":          -1 * np.unwrap(np.array(sad_survey["GCHI2"]))[s_idx],
        "psi":          +1 * np.unwrap(np.array(sad_survey["GCHI3"]))[s_idx],
        "name":         np.array(sad_survey["NAME"])[s_idx],
        "element_type": np.array(sad_survey["TYPE"])[s_idx]})

    # Required to allow any kind of plotting
    dummy_line  = xt.Line()
    sv_sad.line = dummy_line

    ########################################
    # Bend Direction Reversal
    ########################################
    if reverse_survey_horizontal:
        sv_sad.X        *= -1                       # pylint: disable=no-member
        sv_sad.Y        *= +1                       # pylint: disable=no-member
        sv_sad.Z        *= +1                       # pylint: disable=no-member
        sv_sad.theta    *= -1                       # pylint: disable=no-member
        sv_sad.phi      *= +1                       # pylint: disable=no-member
        sv_sad.psi      *= -1                       # pylint: disable=no-member

    ########################################
    # Bend Direction Reversal (Vertical)
    ########################################
    if reverse_survey_vertical:
        sv_sad.X        *= +1                       # pylint: disable=no-member
        sv_sad.Y        *= -1                       # pylint: disable=no-member
        sv_sad.Z        *= +1                       # pylint: disable=no-member
        sv_sad.theta    *= +1                       # pylint: disable=no-member
        sv_sad.phi      *= -1                       # pylint: disable=no-member
        sv_sad.psi      *= -1                       # pylint: disable=no-member

    ########################################
    # Return the TwissTable
    ########################################
    return sv_sad
