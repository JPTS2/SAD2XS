"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess

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
WriteString[of, "FSHIFT = "//FSHIFT//";\\n"];
FFS["output "//of//" type"];
WriteBeamLine[of, ExtractBeamLine[], Format->"MAIN", Name->{{"{line_name}"}}];
Close[of];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    with open("temp_sad_rebuild_lattice.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)

    ########################################
    # Run the process
    ########################################
    try:
        subprocess.run(
            [sad_path, "temp_sad_rebuild_lattice.sad"],
            capture_output  = True,
            text            = True,
            timeout         = wall_time,
            check           = True)
    except subprocess.TimeoutExpired:
        print(f"SAD Twiss timed out at {wall_time}s")
        if os.path.exists("temp_sad_rebuild_lattice.sad"):
            os.remove("temp_sad_rebuild_lattice.sad")
        raise
    except subprocess.CalledProcessError as e:
        print(f"SAD exited with non-zero status {e.returncode}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        if os.path.exists("temp_sad_rebuild_lattice.sad"):
            os.remove("temp_sad_rebuild_lattice.sad")
        raise
    finally:
        if os.path.exists("temp_sad_rebuild_lattice.sad"):
            os.remove("temp_sad_rebuild_lattice.sad")
