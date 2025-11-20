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
# SAD Twiss Print Function
################################################################################
def generate_twiss_print_function():
    """
    TBD
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
# Closed Ring 4D Twiss Function
################################################################################
def twiss_sad(
        lattice_filepath:       str,
        line_name:              str,
        reverse_element_order:  bool    = False,
        reverse_bend_direction: bool    = False,
        closed:                 bool    = True,
        calc6d:                 bool    = False,
        rfsw:                   bool    = True,
        rad:                    bool    = False,
        radcod:                 bool    = False,
        radtaper:               bool    = False,
        delta0:                 float   = 0.0,
        additional_commands:    str     = "",
        wall_time:              int     = 30,
        sad_path:               str     = "sad"):
    """
    Generate a SAD command to compute the twiss parameters of a lattice.
    """

    ########################################
    # Configure Settings
    ########################################
    calc_flag       = "CALC6D;" if calc6d else "CALC4D;"
    closed_flag     = "CELL;" if closed else "INS;"
    rfsw_flag       = "RFSW;" if rfsw else "NORFSW;"
    rad_flag        = "RAD;" if rad else "NORAD;"
    radcod_flag     = "RADCOD;" if radcod else "NORADCOD;"
    radtaper_flag   = "RADTAPER;" if radtaper else ""

    ########################################
    # Generate the twiss command
    ########################################
    print("Creating SAD Command")
    sad_command = f"""OFF ECHO;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Start FFS
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
FFS;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Set FFS flags
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
FFS["{rfsw_flag}{rad_flag}{radcod_flag}{radtaper_flag}NOFLUC;"];

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
SaveTwissFile["./temp_sad_twiss.tfs"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    with open("temp_sad_twiss.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)

    ########################################
    # Run the process
    ########################################
    try:
        subprocess.run(
            [sad_path, "temp_sad_twiss.sad"],
            capture_output  = True,
            text            = True,
            timeout         = wall_time,
            check           = True)
    except subprocess.TimeoutExpired:
        print(f"SAD Twiss timed out at {wall_time}s")
        if os.path.exists("temp_sad_twiss.sad"):
            os.remove("temp_sad_twiss.sad")
        raise
    except subprocess.CalledProcessError as e:
        print(f"SAD exited with non-zero status {e.returncode}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        if os.path.exists("temp_sad_twiss.sad"):
            os.remove("temp_sad_twiss.sad")
        raise
    finally:
        if os.path.exists("temp_sad_twiss.sad"):
            os.remove("temp_sad_twiss.sad")

    ########################################
    # Read the data
    ########################################
    sad_twiss   = tfs.read("temp_sad_twiss.tfs")
    os.remove("temp_sad_twiss.tfs")

    ########################################
    # Convert to TwissTable
    ########################################
    s_idx       = np.argsort(np.array(sad_twiss["S"]), kind = "stable")
    tw_sad      = xt.TwissTable({
        "name":     np.array(sad_twiss["NAME"])[s_idx],
        "s":        np.array(sad_twiss["S"])[s_idx],
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
    # Element Order Reversal
    ########################################
    if reverse_element_order:
        tw_sad.s        = tw_sad.s[-1] - tw_sad.s
        tw_sad.x        *= +1
        tw_sad.px       *= +1 * -1
        tw_sad.y        *= +1
        tw_sad.py       *= +1 * -1
        tw_sad.zeta     = tw_sad.zeta[-1] - tw_sad.zeta
        tw_sad.delta    = tw_sad.delta[-1] - tw_sad.delta
        tw_sad.betx     *= +1
        tw_sad.bety     *= +1
        tw_sad.alfx     *= +1 * -1
        tw_sad.alfy     *= +1 * -1
        tw_sad.dx       *= +1
        tw_sad.dpx      *= +1 * -1
        tw_sad.dy       *= +1
        tw_sad.dpy      *= +1 * -1
        tw_sad.mux      = tw_sad.mux[-1] - tw_sad.mux
        tw_sad.muy      = tw_sad.muy[-1] - tw_sad.muy
        tw_sad.R1       *= +1
        tw_sad.R2       *= +1
        tw_sad.R3       *= +1
        tw_sad.R4       *= +1

        tw_sad.name     = np.flip(tw_sad.name)
        tw_sad.s        = np.flip(tw_sad.s)
        tw_sad.x        = np.flip(tw_sad.x)
        tw_sad.px       = np.flip(tw_sad.px)
        tw_sad.y        = np.flip(tw_sad.y)
        tw_sad.py       = np.flip(tw_sad.py)
        tw_sad.zeta     = np.flip(tw_sad.zeta)
        tw_sad.delta    = np.flip(tw_sad.delta)
        tw_sad.betx     = np.flip(tw_sad.betx)
        tw_sad.bety     = np.flip(tw_sad.bety)
        tw_sad.alfx     = np.flip(tw_sad.alfx)
        tw_sad.alfy     = np.flip(tw_sad.alfy)
        tw_sad.dx       = np.flip(tw_sad.dx)
        tw_sad.dpx      = np.flip(tw_sad.dpx)
        tw_sad.dy       = np.flip(tw_sad.dy)
        tw_sad.dpy      = np.flip(tw_sad.dpy)
        tw_sad.mux      = np.flip(tw_sad.mux)
        tw_sad.muy      = np.flip(tw_sad.muy)
        tw_sad.R1       = np.flip(tw_sad.R1)
        tw_sad.R2       = np.flip(tw_sad.R2)
        tw_sad.R3       = np.flip(tw_sad.R3)
        tw_sad.R4       = np.flip(tw_sad.R4)

    ########################################
    # Bend Direction Reversal
    ########################################
    if reverse_bend_direction:
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
