"""
================================================================================
SAD Helpers: Twiss
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
import tfs
import xtrack as xt

from ._helpers import run_sad, _check_mathematica_output

logger  = logging.getLogger(__name__)

################################################################################
# SAD Twiss Print Function
################################################################################
def generate_twiss_print_function():
    """
    Build the SAD-side `SaveTwissFile[filename_]` function definition.

    Writes lattice length, fractional tunes (Q1/Q2), and every line
    element's Twiss record (NAME, TYPE, S, L, BETX/Y, ALFX/Y, MUX/Y,
    DX/Y, DPX/Y, X/PX/Y/PY, DZ, DELTA, R1-R4) to `filename`, in TFS
    format. Used by `twiss_sad` to extract SAD's Twiss output.

    Returns
    -------
    str
        The SAD command text defining `SaveTwissFile`.
    """

    twiss_command   = """
SaveTwissFile[filename_]:=Module[
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
    WriteString[fn, "@ ",
        StringFill["LENGTH"," ", 20],
        "%le",
        StringFill[ToString[LINE["LENG","$$$"]]," ",-22],
        "\\n"]; 
    WriteString[fn, "@ ",
        StringFill["Q1"," ", 20],
        "%le",
        StringFill[ToString[Twiss["NX","$$$"]/(2*Pi)]," ",-22],
        "\\n"]; 
    WriteString[fn, "@ ",
        StringFill["Q2"," ", 20],
        "%le",
        StringFill[ToString[Twiss["NY","$$$"]/(2*Pi)]," ",-22],
        "\\n"]; 
    WriteString[fn, "* ",
        StringFill["NAME"," ", 20]," ",
        StringFill["TYPE"," ", -12],"    ",
        StringFill["S"," ", -12],"    ",
        StringFill["L"," ", -12],"    ",
        StringFill["BETX"," ", -12],"    ",
        StringFill["BETY"," ", -12],"    ",
        StringFill["ALFX"," ", -12],"    ",
        StringFill["ALFY"," ", -12],"    ",
        StringFill["MUX"," ", -12],"    ",
        StringFill["MUY"," ", -12],"    ",
        StringFill["DX"," ", -12],"    ",
        StringFill["DY"," ", -12],"    ",
        StringFill["DPX"," ", -12],"    ",
        StringFill["DPY"," ", -12],"    ",
        StringFill["X"," ", -12],"    ",
        StringFill["PX"," ", -12],"    ",
        StringFill["Y"," ", -12],"    ",
        StringFill["PY"," ", -12],"    ",
        StringFill["DZ"," ", -12],"    ",
        StringFill["DELTA"," ", -12],"    ",
        StringFill["R1"," ", -12],"    ",
        StringFill["R2"," ", -12],"    ",
        StringFill["R3"," ", -12],"    ",
        StringFill["R4"," ", -12],
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
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],"    ",
        StringFill["%le"," ", -12],
        StringFill["%le"," ", -12],
        "\\n"];
    
    pos = LINE["POSITION","*{^$$$}"];
    Do[
        WriteString[fn,     " ",
            StringFill[StringJoin["\\"",LINE["NAME",pos[i]],"\\""]," ", 21]," ",
            StringFill[StringJoin["\\"",LINE["TYPENAME",pos[i]],"\\""]," ", -12],"    ",
            LINE["LENG",pos[i]],"    ",
            LINE["L",pos[i]],"    ",
            Twiss["BX",pos[i]],"    ",
            Twiss["BY",pos[i]],"    ",
            Twiss["AX",pos[i]],"    ",
            Twiss["AY",pos[i]],"    ",
            Twiss["NX",pos[i]]/(2*Pi),"    ",
            Twiss["NY",pos[i]]/(2*Pi),"    ",
            Twiss["PEX",pos[i]],"    ",
            Twiss["PEY",pos[i]],"    ",
            Twiss["PEPX",pos[i]],"    ",
            Twiss["PEPY",pos[i]],"    ",
            Twiss["DX",pos[i]],"    ",
            Twiss["DPX",pos[i]],"    ",
            Twiss["DY",pos[i]],"    ",
            Twiss["DPY",pos[i]],"    ",
            Twiss["DZ",pos[i]],"    ",
            Twiss["DDP",pos[i]],"    ",
            Twiss["R1",pos[i]],"    ",
            Twiss["R2",pos[i]],"    ",
            Twiss["R3",pos[i]],"    ",
            Twiss["R4",pos[i]],
            "\\n"]
    ,{i, Length[pos]}
    ];
Close[fn];
];
"""
    return twiss_command

################################################################################
# Twiss
################################################################################
def twiss_sad(
        lattice_filepath:       str,
        line_name:              str,
        reverse_element_order:  bool    = False,
        reverse_survey_horizontal: bool    = False,
        closed:                 bool    = True,
        calc6d:                 bool    = False,
        trpt:                   bool    = False,
        rfsw:                   bool    = True,
        rad:                    bool    = False,
        radcod:                 bool    = False,
        radtaper:               bool    = False,
        delta0:                 float   = 0.0,
        additional_commands:    str     = "",
        wall_time:              int     = 30,
        sad_path:               str     = "sad"):
    """
    Compute a lattice's Twiss parameters in real SAD, as an Xsuite
    TwissTable.

    Runs SAD's own Twiss (CELL/INS + CALC4D/CALC6D + COD + CALC),
    reads back the TFS file `generate_twiss_print_function` writes,
    and reassembles the result as an `xt.TwissTable` with column
    names matching Xsuite's convention.

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file, relative to the current working
        directory (SAD changes into the script's own directory, so
        the lattice must be reachable from there).
    line_name : str
        The SAD line to USE.
    reverse_element_order : bool, optional
        Reverse the line's element order natively in SAD (via
        `-ExtractBeamLine[]`) before computing Twiss. Defaults to
        False.
    reverse_survey_horizontal : bool, optional
        Flip the sign of the horizontal-plane columns in the returned
        Twiss (mirrors `reverse_line_survey_horizontal`'s
        convention). Defaults to False.
    closed : bool, optional
        If True, treat the lattice as a closed ring (SAD's CELL); if
        False, as a transfer line (SAD's INS). Defaults to True.
    calc6d : bool, optional
        If True, use SAD's CALC6D (longitudinal + transverse); if
        False, CALC4D (transverse only). Defaults to False.
    trpt : bool, optional
        If True, declare the beam line a transport line rather than
        part of a storage ring (SAD's TRPT flag, antonym RING): the
        nominal/reference momentum is carried along the line by
        accelerating elements, rather than held fixed at the line's
        initial MOMENTUM. Independent of rfsw/rad/radcod -- see
        docs/sad-behaviour.md for the physics this controls. Defaults
        to False.
    rfsw : bool, optional
        Enable RF cavities (SAD's RFSW flag). Defaults to True.
    rad : bool, optional
        Enable radiation effects (SAD's RAD flag). Defaults to False.
    radcod : bool, optional
        Include radiation damping in the closed-orbit search (SAD's
        RADCOD flag). Defaults to False.
    radtaper : bool, optional
        Enable RF/orbit tapering for radiation (SAD's RADTAPER flag).
        Defaults to False.
    delta0 : float, optional
        Reference momentum offset (SAD's DP0). Defaults to 0.0.
    additional_commands : str, optional
        Extra SAD commands run after loading the line and before the
        Twiss. Defaults to "".
    wall_time : int, optional
        Timeout, in seconds, for the SAD subprocess. Defaults to 30.
    sad_path : str, optional
        Path to the SAD executable. Defaults to "sad".

    Returns
    -------
    xt.TwissTable
        The lattice's Twiss parameters, ordered by s. Also carries
        "qx", "qy", and "circumference" as table-level attributes.

    Raises
    ------
    RuntimeError
        If the SAD subprocess times out or exits non-zero (see
        `run_sad`).
    ValueError
        If SAD's output contains a Mathematica undefined-symbol
        marker (see `_check_mathematica_output`), or the TFS output
        cannot be parsed (a physically degenerate lattice
        configuration).
    """

    ########################################
    # Configure Settings
    ########################################
    calc_flag       = "CALC6D;" if calc6d else "CALC4D;"
    closed_flag     = "CELL;" if closed else "INS;"
    trpt_flag       = "TRPT;" if trpt else "RING;"
    rfsw_flag       = "RFSW;" if rfsw else "NORFSW;"
    rad_flag        = "RAD;" if rad else "NORAD;"
    radcod_flag     = "RADCOD;" if radcod else "NORADCOD;"
    radtaper_flag   = "RADTAPER;" if radtaper else ""

    ########################################
    # Generate the twiss command
    ########################################
    uid      = uuid.uuid4().hex[:12]
    cmd_file = f"_sad_twiss_{uid}.sad"
    out_file = f"_sad_twiss_{uid}.tfs"

    # Native SAD reversal via a live ExtractBeamLine[] -- see docs/sad-behaviour.md.
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Set FFS flags
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
FFS["{trpt_flag}{rfsw_flag}{rad_flag}{radcod_flag}{radtaper_flag}NOFLUC;"];

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
! 6D Emittance Twiss
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{closed_flag}
{calc_flag}
DP0 = {delta0};
COD;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Include the twiss print function
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{generate_twiss_print_function()}
SaveTwissFile["./{out_file}"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    try:
        run_sad(
            sad_command = sad_command,
            cmd_file    = cmd_file,
            task_name   = "twiss",
            wall_time   = wall_time,
            sad_path    = sad_path)

        with open(out_file, encoding="utf-8") as _f:
            _raw = _f.read()
        _check_mathematica_output(_raw)

        try:
            sad_twiss = tfs.read(out_file)
        except Exception as exc:
            raise ValueError(
                f"The lattice configuration is physically degenerate "
                f"— TFS output could not be parsed: {exc}") from exc

    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

    ########################################
    # Convert to TwissTable
    ########################################
    s_idx       = np.argsort(np.array(sad_twiss["S"]), kind = "stable")
    tw_sad      = xt.TwissTable({
        "name":         np.array(sad_twiss["NAME"])[s_idx],
        "s":            np.array(sad_twiss["S"])[s_idx],
        "element_type": np.array(sad_twiss["TYPE"])[s_idx],
        "length":       np.array(sad_twiss["L"])[s_idx],
        "x":        np.array(sad_twiss["X"])[s_idx],
        "px":       np.array(sad_twiss["PX"])[s_idx],
        "y":        np.array(sad_twiss["Y"])[s_idx],
        "py":       np.array(sad_twiss["PY"])[s_idx],
        "zeta":     np.array(sad_twiss["DZ"])[s_idx],
        "delta":    np.array(sad_twiss["DELTA"])[s_idx],
        "betx":     np.array(sad_twiss["BETX"])[s_idx],
        "bety":     np.array(sad_twiss["BETY"])[s_idx],
        "alfx":     np.array(sad_twiss["ALFX"])[s_idx],
        "alfy":     np.array(sad_twiss["ALFY"])[s_idx],
        "dx":       np.array(sad_twiss["DX"])[s_idx],
        "dpx":      np.array(sad_twiss["DPX"])[s_idx],
        "dy":       np.array(sad_twiss["DY"])[s_idx],
        "dpy":      np.array(sad_twiss["DPY"])[s_idx],
        "mux":      np.array(sad_twiss["MUX"])[s_idx],
        "muy":      np.array(sad_twiss["MUY"])[s_idx],
        "R1":       np.array(sad_twiss["R1"])[s_idx],
        "R2":       np.array(sad_twiss["R2"])[s_idx],
        "R3":       np.array(sad_twiss["R3"])[s_idx],
        "R4":       np.array(sad_twiss["R4"])[s_idx]})
    tw_sad["qx"]            = sad_twiss["Q1"]
    tw_sad["qy"]            = sad_twiss["Q2"]
    tw_sad["circumference"] = sad_twiss["LENGTH"]

    ########################################
    # Bend Direction Reversal
    ########################################
    if reverse_survey_horizontal:
        tw_sad.x        *= -1
        tw_sad.px       *= -1
        tw_sad.y        *= +1
        tw_sad.py       *= +1
        tw_sad.zeta     *= +1
        tw_sad.delta    *= +1
        tw_sad.betx     *= +1
        tw_sad.bety     *= +1
        tw_sad.alfx     *= +1
        tw_sad.alfy     *= +1
        tw_sad.dx       *= -1
        tw_sad.dpx      *= -1
        tw_sad.dy       *= +1
        tw_sad.dpy      *= +1
        tw_sad.mux      *= +1
        tw_sad.muy      *= +1
        tw_sad.R1       *= +1
        tw_sad.R2       *= +1
        tw_sad.R3       *= +1
        tw_sad.R4       *= +1

    ########################################
    # Return the TwissTable
    ########################################
    return tw_sad

################################################################################
# Add second order dispersions to twiss
################################################################################
def compute_second_order_dispersions(
        lattice_filepath:       str,
        line_name:              str,
        sad_twiss:              xt.TwissTable | None    = None,
        reverse_element_order:  bool                    = False,
        reverse_survey_horizontal: bool                    = False,
        closed:                 bool                    = True,
        calc6d:                 bool                    = False,
        rfsw:                   bool                    = True,
        rad:                    bool                    = False,
        radcod:                 bool                    = False,
        radtaper:               bool                    = False,
        delta0:                 float                   = 0.0,
        ddelta:                 float                   = 1E-4,
        additional_commands:    str                     = "",
        wall_time:              int                     = 60,
        sad_path:               str                     = "sad"):
    """
    Compute second-order dispersions and add them to a Twiss table.

    Runs `twiss_sad` twice (at `delta0` and `delta0 + ddelta`) and
    finite-differences the result: ddx = 2 * (x(delta0+ddelta) -
    x(delta0) - dx(delta0) * ddelta) / ddelta**2 (and equivalently for
    px/y/py). With thanks to G. Broggi for the method.

    If `sad_twiss` is given, its s/x/px/y/py/zeta/delta columns are
    checked against the on-momentum Twiss computed here as a
    consistency guard before adding the new columns.

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file.
    line_name : str
        The SAD line to USE.
    sad_twiss : xt.TwissTable or None, optional
        An existing Twiss table to add the second-order-dispersion
        columns to. If None, the on-momentum Twiss computed here is
        used and returned. Defaults to None.
    reverse_element_order, reverse_survey_horizontal, closed, calc6d : bool
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    rfsw, rad, radcod, radtaper : bool
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    delta0 : float, optional
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    additional_commands : str, optional
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    wall_time : int, optional
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    sad_path : str, optional
        Forwarded to `twiss_sad` for both the on- and off-momentum
        Twiss calls.
    ddelta : float, optional
        The momentum-offset step used for the finite difference.
        Defaults to 1E-4.

    Returns
    -------
    xt.TwissTable
        `sad_twiss` (or the newly computed on-momentum Twiss, if
        `sad_twiss` was None), with "ddx", "ddpx", "ddy", "ddpy"
        columns added.

    Raises
    ------
    AssertionError
        If `sad_twiss` is given and its s/x/px/y/py/zeta/delta
        columns do not match the on-momentum Twiss computed here.
    """

    ########################################
    # Compute twiss at delta0
    ########################################
    tw_on   = twiss_sad(
        lattice_filepath        = lattice_filepath,
        line_name               = line_name,
        reverse_element_order   = reverse_element_order,
        reverse_survey_horizontal  = reverse_survey_horizontal,
        closed                  = closed,
        calc6d                  = calc6d,
        rfsw                    = rfsw,
        rad                     = rad,
        radcod                  = radcod,
        radtaper                = radtaper,
        delta0                  = delta0,
        additional_commands     = additional_commands,
        wall_time               = wall_time,
        sad_path                = sad_path)

    # If a reference twiss is provided, check consistency
    if sad_twiss is not None:
        assert np.allclose(tw_on.s, sad_twiss.s), \
            "Twiss s positions do not match!"
        assert np.allclose(tw_on.x, sad_twiss.x), \
            "Twiss x positions do not match!"
        assert np.allclose(tw_on.px, sad_twiss.px), \
            "Twiss px positions do not match!"
        assert np.allclose(tw_on.y, sad_twiss.y), \
            "Twiss y positions do not match!"
        assert np.allclose(tw_on.py, sad_twiss.py), \
            "Twiss py positions do not match!"
        assert np.allclose(tw_on.zeta, sad_twiss.zeta), \
            "Twiss zeta positions do not match!"
        assert np.allclose(tw_on.delta, sad_twiss.delta), \
            "Twiss delta positions do not match!"

    ########################################
    # Compute off momentum twiss at delta0 + ddelta
    ########################################
    tw_off  = twiss_sad(
        lattice_filepath        = lattice_filepath,
        line_name               = line_name,
        reverse_element_order   = reverse_element_order,
        reverse_survey_horizontal  = reverse_survey_horizontal,
        closed                  = closed,
        calc6d                  = calc6d,
        rfsw                    = rfsw,
        rad                     = rad,
        radcod                  = radcod,
        radtaper                = radtaper,
        delta0                  = delta0 + ddelta,
        additional_commands     = additional_commands,
        wall_time               = wall_time,
        sad_path                = sad_path)

    ########################################
    # Obtain required data
    ########################################
    x_on    = tw_on.x
    x_off   = tw_off.x
    dx_on   = tw_on.dx

    px_on   = tw_on.px
    px_off  = tw_off.px
    dpx_on  = tw_on.dpx

    y_on    = tw_on.y
    y_off   = tw_off.y
    dy_on   = tw_on.dy

    py_on   = tw_on.py
    py_off  = tw_off.py
    dpy_on  = tw_on.dpy

    ########################################
    # Compute second order dispersions
    ########################################
    ddx     = 2 * (x_off - x_on - dx_on * ddelta) / (ddelta**2)
    ddpx    = 2 * (px_off - px_on - dpx_on * ddelta) / (ddelta**2)
    ddy     = 2 * (y_off - y_on - dy_on * ddelta) / (ddelta**2)
    ddpy    = 2 * (py_off - py_on - dpy_on * ddelta) / (ddelta**2)

    ########################################
    # Add these values to the twiss
    ########################################
    if sad_twiss is None:
        sad_twiss   = tw_on

    sad_twiss["ddx"]    = ddx
    sad_twiss["ddpx"]   = ddpx
    sad_twiss["ddy"]    = ddy
    sad_twiss["ddpy"]   = ddpy

    ########################################
    # Return the twiss
    ########################################
    return sad_twiss

################################################################################
# Add chromatic functions
################################################################################
def compute_chromatic_functions(
        lattice_filepath:       str,
        line_name:              str,
        sad_twiss:              xt.TwissTable | None    = None,
        reverse_element_order:  bool                    = False,
        reverse_survey_horizontal: bool                    = False,
        closed:                 bool                    = True,
        calc6d:                 bool                    = False,
        rfsw:                   bool                    = True,
        rad:                    bool                    = False,
        radcod:                 bool                    = False,
        radtaper:               bool                    = False,
        delta0:                 float                   = 0.0,
        ddelta:                 float                   = 1E-4,
        additional_commands:    str                     = "",
        wall_time:              int                     = 60,
        sad_path:               str                     = "sad"):
    """
    Compute the chromatic functions (MAD8-convention Wx/Wy) and add
    them to a Twiss table.

    Runs `twiss_sad` three times (at delta0, delta0 + ddelta, and
    delta0 - ddelta) and central-differences beta/alpha to build the
    chromatic amplitude/phase functions, following MAD8 physics
    manual section 6.3. With thanks to G. Broggi for the method.

    If `sad_twiss` is given, its s/x/px/y/py/zeta/delta columns are
    checked against the on-momentum Twiss computed here as a
    consistency guard before adding the new columns.

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file.
    line_name : str
        The SAD line to USE.
    sad_twiss : xt.TwissTable or None, optional
        An existing Twiss table to add the chromatic-function columns
        to. If None, the on-momentum Twiss computed here is used and
        returned. Defaults to None.
    reverse_element_order, reverse_survey_horizontal, closed, calc6d : bool
        Forwarded to `twiss_sad` for all three Twiss calls.
    rfsw, rad, radcod, radtaper : bool
        Forwarded to `twiss_sad` for all three Twiss calls.
    delta0 : float, optional
        Forwarded to `twiss_sad` for all three Twiss calls.
    additional_commands : str, optional
        Forwarded to `twiss_sad` for all three Twiss calls.
    wall_time : int, optional
        Forwarded to `twiss_sad` for all three Twiss calls.
    sad_path : str, optional
        Forwarded to `twiss_sad` for all three Twiss calls.
    ddelta : float, optional
        The momentum-offset step used for the central difference.
        Defaults to 1E-4.

    Returns
    -------
    xt.TwissTable
        `sad_twiss` (or the newly computed on-momentum Twiss, if
        `sad_twiss` was None), with "bx_chrom", "by_chrom",
        "ax_chrom", "ay_chrom", "wx_chrom", "wy_chrom" columns added.

    Raises
    ------
    AssertionError
        If `sad_twiss` is given and its s/x/px/y/py/zeta/delta
        columns do not match the on-momentum Twiss computed here.
    """

    ########################################
    # Compute twiss at delta0
    ########################################
    tw_on   = twiss_sad(
        lattice_filepath        = lattice_filepath,
        line_name               = line_name,
        reverse_element_order   = reverse_element_order,
        reverse_survey_horizontal  = reverse_survey_horizontal,
        closed                  = closed,
        calc6d                  = calc6d,
        rfsw                    = rfsw,
        rad                     = rad,
        radcod                  = radcod,
        radtaper                = radtaper,
        delta0                  = delta0,
        additional_commands     = additional_commands,
        wall_time               = wall_time,
        sad_path                = sad_path)

    # If a reference twiss is provided, check consistency
    if sad_twiss is not None:
        assert np.allclose(tw_on.s, sad_twiss.s), \
            "Twiss s positions do not match!"
        assert np.allclose(tw_on.x, sad_twiss.x), \
            "Twiss x positions do not match!"
        assert np.allclose(tw_on.px, sad_twiss.px), \
            "Twiss px positions do not match!"
        assert np.allclose(tw_on.y, sad_twiss.y), \
            "Twiss y positions do not match!"
        assert np.allclose(tw_on.py, sad_twiss.py), \
            "Twiss py positions do not match!"
        assert np.allclose(tw_on.zeta, sad_twiss.zeta), \
            "Twiss zeta positions do not match!"
        assert np.allclose(tw_on.delta, sad_twiss.delta), \
            "Twiss delta positions do not match!"

    ########################################
    # Compute off momentum twiss at delta0 + ddelta
    ########################################
    tw_plus  = twiss_sad(
        lattice_filepath        = lattice_filepath,
        line_name               = line_name,
        reverse_element_order   = reverse_element_order,
        reverse_survey_horizontal  = reverse_survey_horizontal,
        closed                  = closed,
        calc6d                  = calc6d,
        rfsw                    = rfsw,
        rad                     = rad,
        radcod                  = radcod,
        radtaper                = radtaper,
        delta0                  = delta0 + ddelta,
        additional_commands     = additional_commands,
        wall_time               = wall_time,
        sad_path                = sad_path)

    ########################################
    # Compute off momentum twiss at delta0 - ddelta
    ########################################
    tw_minus    = twiss_sad(
        lattice_filepath        = lattice_filepath,
        line_name               = line_name,
        reverse_element_order   = reverse_element_order,
        reverse_survey_horizontal  = reverse_survey_horizontal,
        closed                  = closed,
        calc6d                  = calc6d,
        rfsw                    = rfsw,
        rad                     = rad,
        radcod                  = radcod,
        radtaper                = radtaper,
        delta0                  = delta0 - ddelta,
        additional_commands     = additional_commands,
        wall_time               = wall_time,
        sad_path                = sad_path)

    ########################################
    # Obtain required data
    ########################################
    betx_on     = tw_on.betx
    betx_plus   = tw_plus.betx
    betx_minus  = tw_minus.betx

    bety_on     = tw_on.bety
    bety_plus   = tw_plus.bety
    bety_minus  = tw_minus.bety

    alfx_on     = tw_on.alfx
    alfx_plus   = tw_plus.alfx
    alfx_minus  = tw_minus.alfx

    alfy_on     = tw_on.alfy
    alfy_plus   = tw_plus.alfy
    alfy_minus  = tw_minus.alfy

    ########################################
    # Compute chromatic functions
    ########################################
    # See MAD8 physics manual section 6.3
    dbetx      = (betx_plus - betx_minus) / (2 * ddelta)
    dbety      = (bety_plus - bety_minus) / (2 * ddelta)
    dalfx      = (alfx_plus - alfx_minus) / (2 * ddelta)
    dalfy      = (alfy_plus - alfy_minus) / (2 * ddelta)

    bx_chrom   = dbetx / betx_on
    by_chrom   = dbety / bety_on

    ax_chrom   = dalfx - dbetx * alfx_on / betx_on
    ay_chrom   = dalfy - dbety * alfy_on / bety_on

    wx_chrom   = np.sqrt(ax_chrom**2 + bx_chrom**2)
    wy_chrom   = np.sqrt(ay_chrom**2 + by_chrom**2)

    ########################################
    # Add these values to the twiss
    ########################################
    if sad_twiss is None:
        sad_twiss   = tw_on

    sad_twiss["bx_chrom"]    = bx_chrom
    sad_twiss["by_chrom"]    = by_chrom
    sad_twiss["ax_chrom"]    = ax_chrom
    sad_twiss["ay_chrom"]    = ay_chrom
    sad_twiss["wx_chrom"]    = wx_chrom
    sad_twiss["wy_chrom"]    = wy_chrom

    ########################################
    # Return the twiss
    ########################################
    return sad_twiss
