"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
import ast
import numpy as np

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
CELL;
COD;
CALC;
SAVE ALL;

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Include the off momentum tune function
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{generate_off_momentum_tune_function()}

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Scan chromaticity
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
d = Table[
    tunes   = CalculateOffMomentumTune[x];
    {{x, tunes[1], tunes[2]}},
    {{x, -{dp_extent}, {dp_extent}, {dp_step} }}];
Print[d];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    with open("temp_sad_chromaticity.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)

    ########################################
    # Run the process
    ########################################
    try:
        process = subprocess.run(
            [sad_path, "temp_sad_chromaticity.sad"],
            capture_output  = True,
            text            = True,
            timeout         = wall_time,
            check           = True)
    except subprocess.TimeoutExpired:
        print(f"SAD Twiss timed out at {wall_time}s")
        if os.path.exists("temp_sad_chromaticity.sad"):
            os.remove("temp_sad_chromaticity.sad")
        raise
    except subprocess.CalledProcessError as e:
        print(f"SAD exited with non-zero status {e.returncode}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        if os.path.exists("temp_sad_chromaticity.sad"):
            os.remove("temp_sad_chromaticity.sad")
        raise
    finally:
        if os.path.exists("temp_sad_chromaticity.sad"):
            os.remove("temp_sad_chromaticity.sad")

    ########################################
    # Read the data
    ########################################
    raw = process.stdout

    ########################################
    # Process the output
    ########################################
    start   = raw.find("{{")
    end     = raw.rfind("}}")
    if start == -1 or end == -1:
        raise ValueError("Table not found in subprocess output")
    matrix_str = raw[start:end + 2]

    ########################################
    # Convert to numpy array
    ########################################
    cleaned     = matrix_str.replace("}", "]").replace("{", "[")
    matrix_list = ast.literal_eval(cleaned)
    chrom_scan  = np.array(matrix_list, dtype = float)

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
