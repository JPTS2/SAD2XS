"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
import uuid
import ast
import numpy as np

from ._helpers import _check_mathematica_output

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

    Returns
    -------
    np.ndarray
        The transfer matrix as a NumPy array.
    """

    ########################################
    # Ensure both or neither of start_element and end_element are provided
    ########################################
    if start_element is not None and end_element is None:
        raise ValueError("If start_element is provided, end_element must also be provided")
    if start_element is None and end_element is not None:
        raise ValueError("If end_element is provided, start_element must also be provided")

    print("Creating SAD Command")

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
        with open(cmd_file, "w", encoding = "utf-8") as f:
            f.write(sad_command)

        try:
            subprocess.run(
                [sad_path, cmd_file],
                capture_output = True,
                text           = True,
                timeout        = wall_time,
                check          = True)
        except subprocess.TimeoutExpired:
            print(f"SAD Twiss timed out at {wall_time}s")
            raise
        except subprocess.CalledProcessError as e:
            print(f"SAD exited with non-zero status {e.returncode}")
            print("stdout:", e.stdout)
            print("stderr:", e.stderr)
            raise

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
        for path in [cmd_file, out_file]:
            if os.path.exists(path):
                os.remove(path)

    return rmatrix
