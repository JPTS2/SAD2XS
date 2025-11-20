"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
import numpy as np
import tfs
import xtrack as xt

################################################################################
# SAD Survey Print Function
################################################################################
def generate_survey_print_function():
    """
    TBD
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
        lattice_filepath:       str,
        line_name:              str,
        closed:                 bool    = True,
        reverse_element_order:  bool    = False,
        reverse_bend_direction: bool    = False,
        additional_commands:    str     = "",
        wall_time:              int     = 30,
        sad_path:               str     = "sad"):
    """
    Generate a SAD command to compute the twiss parameters of a lattice.
    """

    ########################################
    # Configure Settings
    ########################################
    closed_flag = "CELL;" if closed else "INS;"

    ########################################
    # Generate the twiss command
    ########################################
    print("Creating SAD Command")
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
{closed_flag}
COD;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Include the survey print function
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{generate_survey_print_function()}
SaveSurveyFile["./temp_sad_survey.tfs"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    with open("temp_sad_survey.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)

    ########################################
    # Run the process
    ########################################
    try:
        subprocess.run(
            [sad_path, "temp_sad_survey.sad"],
            capture_output  = True,
            text            = True,
            timeout         = wall_time,
            check           = True)
    except subprocess.TimeoutExpired:
        print(f"SAD Twiss timed out at {wall_time}s")
        if os.path.exists("temp_sad_survey.sad"):
            os.remove("temp_sad_survey.sad")
        raise
    except subprocess.CalledProcessError as e:
        print(f"SAD exited with non-zero status {e.returncode}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        if os.path.exists("temp_sad_survey.sad"):
            os.remove("temp_sad_survey.sad")
        raise
    finally:
        if os.path.exists("temp_sad_survey.sad"):
            os.remove("temp_sad_survey.sad")

    ########################################
    # Read the data
    ########################################
    sad_survey   = tfs.read("temp_sad_survey.tfs")
    os.remove("temp_sad_survey.tfs")

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
        "COORD":        "XYShift",
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
    # Element Order Reversal
    ########################################
    if reverse_element_order:
        sv_sad.s        = sv_sad.s[-1] - sv_sad.s
        sv_sad.X        *= +1                       # pylint: disable=no-member
        sv_sad.Y        *= +1                       # pylint: disable=no-member
        sv_sad.Z        *= +1                       # pylint: disable=no-member
        sv_sad.theta    *= +1                       # pylint: disable=no-member
        sv_sad.phi      *= +1                       # pylint: disable=no-member
        sv_sad.psi      *= +1                       # pylint: disable=no-member

    ########################################
    # Bend Direction Reversal
    ########################################
    if reverse_bend_direction:
        sv_sad.X        *= -1                       # pylint: disable=no-member
        sv_sad.Y        *= +1                       # pylint: disable=no-member
        sv_sad.Z        *= +1                       # pylint: disable=no-member
        sv_sad.theta    *= -1                       # pylint: disable=no-member
        sv_sad.phi      *= +1                       # pylint: disable=no-member
        sv_sad.psi      *= -1                       # pylint: disable=no-member

    ########################################
    # Return the TwissTable
    ########################################
    return sv_sad
