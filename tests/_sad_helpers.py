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
    Generate a symmetric log-spaced array of length n_points:
      - Positive values: logspace from 10**upper_power down to 10**lower_power
      - (If n_points is odd) a zero in the center
      - Negative values: the mirror image of the positive side
    
    Args:
      lower_power (float): exponent for the smallest magnitude (linthresh), e.g. -12 → 1e-12
      upper_power (float): exponent for the largest magnitude,       e.g. -9  → 1e-9
      n_points    (int):   total length of the array
    
    Returns:
      numpy.ndarray of shape (n_points,)
    """

    TWISS_COMMAND = f"""
! -------------------------------- PRINT TWISS OF THE RING ---------------------
SaveTwissFile[filename_]:=Module[
{{fn, pos}},
fn=OpenWrite[filename];    ! Use OpenAppend[] if you do not wish to overwrite file
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
WriteString[fn, "@ ",
                StringFill["BETXMAX"," ", 20],
                "%le",
                StringFill[ToString[Max[Twiss["BX","*"]]]," ",-22],
                "\\n"]; 
WriteString[fn, "@ ",
                StringFill["BETYMAX"," ", 20],
                "%le",
                StringFill[ToString[Max[Twiss["BY","*"]]]," ",-22],
                "\\n"]; 
WriteString[fn, "* ",
                StringFill["NAME"," ", 20]," ",
                StringFill["KEYWORD"," ", -12],"    ",
                StringFill["S"," ", -12],"    ",
                StringFill["L"," ", -12],"    ",
                StringFill["BETX"," ", -12],"    ",
                StringFill["BETY"," ", -12],"    ",
                StringFill["ALFX"," ", -12],"    ",
                StringFill["ALFY"," ", -12],"    ",
                StringFill["MUX"," ", -12],"    ",
                StringFill["MUY"," ", -12],"    ",
                StringFill["DX"," ", -12],"    ",
                StringFill["DX_DC"," ", -12],"    ",
                StringFill["DY"," ", -12],"    ",
                StringFill["DY_DC"," ", -12],"    ",
                StringFill["DPX"," ", -12],"    ",
                StringFill["DPX_DC"," ", -12],"    ",
                StringFill["DPY"," ", -12],"    ",
                StringFill["DPY_DC"," ", -12],"    ",
                StringFill["X"," ", -12],"    ",
                StringFill["PX"," ", -12],"    ",
                StringFill["Y"," ", -12],"    ",
                StringFill["PY"," ", -12],"    ",
                StringFill["DELTA"," ", -12],"    ",
                StringFill["GEO_X"," ", -12],"    ",
                StringFill["GEO_Y"," ", -12],"    ",
                StringFill["GEO_Z"," ", -12],"    ",
                StringFill["K0L"," ", -12],"    ",
                StringFill["K1L"," ", -12],"    ",
                StringFill["K2L"," ", -12],"    ",
                StringFill["BZ"," ", -12],"    ",
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
pos=LINE["POSITION","*{{^$$$}}"]; ! Getting positions of elements 
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
                        Twiss["EX",pos[i]],"    ",
                        Twiss["PEY",pos[i]],"    ",
                        Twiss["EY",pos[i]],"    ",
                        Twiss["PEPX",pos[i]],"    ",
                        Twiss["EPX",pos[i]],"    ",
                        Twiss["PEPY",pos[i]],"    ",
                        Twiss["EPY",pos[i]],"    ",
                        Twiss["DX",pos[i]],"    ",
                        Twiss["DPX",pos[i]],"    ",
                        Twiss["DY",pos[i]],"    ",
                        Twiss["DPY",pos[i]],"    ",
                        Twiss["DDP",pos[i]],"    ",
                        LINE["GX",pos[i]],"    ",
                        LINE["GY",pos[i]],"    ",
                        LINE["GZ",pos[i]],"    ",
                        LINE["K0",pos[i]],"    ",
                        LINE["K1",pos[i]],"    ",
                        LINE["K2",pos[i]],"    ",
                        LINE["BZ",pos[i]],"    ",
                        Twiss["R1",pos[i]],"    ",
                        Twiss["R2",pos[i]],"    ",
                        Twiss["R3",pos[i]],"    ",
                        Twiss["R4",pos[i]],
                        "\\n"
                ]
    ,{{i,Length[pos]}}
    ];
Close[fn];
];
    """

    return TWISS_COMMAND

################################################################################
# SAD Twiss Function
################################################################################
def sad_twiss(
        lattice_filename:       str = 'sad_lattice.sad',
        line_name:              str = 'TEST_LINE'):
    """
    Generate a SAD command to compute the twiss parameters of a lattice.
    """
    
    ########################################
    # Generate the twiss command
    ########################################
    SAD_COMMAND = f"""
FFS;

GetMAIN["./{lattice_filename}"];  (* Input your lattice file before modification *)

USE {line_name};

INS;    ! Transfer Line
CALC;   ! Twiss
SAVE ALL;

{generate_twiss_print_function()}

SaveTwissFile["./temporary_sad_twiss.tfs"];

abort;
"""

    ########################################
    # Write and execute the SAD command
    ########################################
    with open("temporary_sad_twiss.sad", "w") as f:
        f.write(SAD_COMMAND)

    subprocess.run(
        ["sad", "temporary_sad_twiss.sad"],
        capture_output  = True,
        text            = True,
        timeout         = 30)
    
    ########################################
    # Read the data into an xtrack TwissTable
    ########################################
    sad_twiss   = tfs.read("temporary_sad_twiss.tfs")
    tw_sad      = xt.TwissTable({
        'name':     np.array(sad_twiss['NAME']),
        's':        np.array(sad_twiss['S']),
        'betx':     np.array(sad_twiss['BETX']),
        'bety':     np.array(sad_twiss['BETY']),
        'alfx':     np.array(sad_twiss['ALFX']),
        'alfy':     np.array(sad_twiss['ALFY']),
        'dx':       np.array(sad_twiss['DX']),
        'dy':       np.array(sad_twiss['DY']),
        'dpx':      np.array(sad_twiss['DPX']),
        'dpy':      np.array(sad_twiss['DPY']),
        'mux':      np.array(sad_twiss['MUX']),
        'muy':      np.array(sad_twiss['MUY']),
        'x':        np.array(sad_twiss['X']),
        'px':       np.array(sad_twiss['PX']),
        'y':        np.array(sad_twiss['Y']),
        'py':       np.array(sad_twiss['PY'])})
    
    ########################################
    # Remove temporary files
    ########################################
    os.remove("temporary_sad_twiss.sad")
    os.remove("temporary_sad_twiss.tfs")

    ########################################
    # Return the TwissTable
    ########################################
    return tw_sad

################################################################################
# Rebuild SAD lattice (post GEO for solenoid)
################################################################################
def rebuild_sad_lattice(
        lattice_filename:       str = 'sad_lattice.sad',
        line_name:              str = 'TEST_LINE'):
    """
    Generate a SAD command to compute the twiss parameters of a lattice.
    """
    
    ########################################
    # Generate the twiss command
    ########################################
    SAD_COMMAND = f"""
FFS;

GetMAIN["./{lattice_filename}"];  (* Input your lattice file before modification *)

USE {line_name};

INS;    ! Transfer Line
CALC;   ! Twiss
SAVE ALL;

of=OpenWrite["./{lattice_filename}"];
WriteString[of, "MOMENTUM = "//MOMENTUM//";\\n"];
WriteString[of, "FSHIFT = 0;\\n"];
FFS["output "//of//" type"];                     (* Write element definition *)
WriteBeamLine[of, ExtractBeamLine[], Format->"MAIN", Name->{{"{line_name}"}}];  (* Write lattice order *)
Close[of];

abort;
"""

    ########################################
    # Write and execute the SAD command
    ########################################
    with open("temporary_sad_twiss.sad", "w") as f:
        f.write(SAD_COMMAND)

    subprocess.run(
        ["sad", "temporary_sad_twiss.sad"],
        capture_output  = True,
        text            = True,
        timeout         = 30)

    ########################################
    # Remove temporary files
    ########################################
    os.remove("temporary_sad_twiss.sad")
