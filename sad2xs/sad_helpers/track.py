"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess
import re
import time
import textwrap
import numpy as np
from tqdm import tqdm

################################################################################
# Track Particles
################################################################################
def track_sad(
        lattice_filepath:       str,
        line_name:              str,
        x_init:                 np.ndarray,
        px_init:                np.ndarray,
        y_init:                 np.ndarray,
        py_init:                np.ndarray,
        zeta_init:              np.ndarray,
        delta_init:             np.ndarray,
        n_turns:                int,
        rfsw:                   bool        = True,
        rad:                    bool        = False,
        fluc:                   bool        = False,
        radcod:                 bool        = False,
        radtaper:               bool        = False,
        turn_by_turn_monitor:   bool        = False,
        with_progress:          bool | int  = True,
        n_cores_max:            int         = 1,
        wall_time:              int         = 24*60*60,
        sad_path:               str         = "sad") -> dict:
    """
    Track particles in SAD

    Parameters
    ----------
    lattice_filepath : str
        Path to the SAD lattice file.
    line_name : str
        Name of the line in the SAD file.
    x_init, px_init, y_init, py_init, zeta_init, delta_init : np.ndarray
        Initial conditions for the particles.
    n_turns : int
        Number of turns to track.
    turn_by_turn_monitor : bool, default False
        If True, return turn-by-turn data.
    rfsw : bool, default True
        If True, enable RF cavities.
    rad : bool, default False
        If True, enable radiation effects.
    radcod : bool, default False
        If True, enable radiation code.
    fluc : bool, default False
        If True, enable quantum radiation effects.
    radtaper : bool, default False
        If True, enable radiation tapering.
    n_cores_max : int, default 1
        Maximum number of cores to use.
    with_progress : bool or int, default True
        If True or int, show progress every "int" turns.
    wall_time : int, default 86400
        Maximum wall time in seconds for the SAD process.
    sad_path : str, default "sad"
        Path to the SAD executable.
        If installed via SAD2XS install_sad_macos, this should be set to the alias "sad".

    Returns
    -------
    dict
        Dictionary containing the tracked particle data.
        Entries are:
        - "x", "px", "y", "py", "zeta", "delta", "state"
        If turn_by_turn_monitor is True, each entry has shape (n_particles, n_turns + 1),
        otherwise shape (n_particles,).
    """

    ########################################
    # Print
    ########################################
    print("#" * 40 + "\n" + "Tracking in SAD" + "\n" + "#" * 40)

    ########################################
    # Assertions
    ########################################
    # Check types of the initial conditions
    assert isinstance(x_init, np.ndarray), "x_init must be a numpy array"
    assert isinstance(px_init, np.ndarray), "px_init must be a numpy array"
    assert isinstance(y_init, np.ndarray), "y_init must be a numpy array"
    assert isinstance(py_init, np.ndarray), "py_init must be a numpy array"
    assert isinstance(zeta_init, np.ndarray), "zeta_init must be a numpy array"
    assert isinstance(delta_init, np.ndarray), "delta_init must be a numpy array"

    # Ensure all arrays are the same length
    assert x_init.shape == px_init.shape == y_init.shape \
        == py_init.shape == zeta_init.shape == delta_init.shape, \
        "All initial condition arrays must be the same shape"

    ########################################
    # Get the number of particles
    ########################################
    n_particles = x_init.shape[0]
    assert n_particles > 0, \
        "Number of particles must be greater than zero"
    assert n_particles <= 1E6, \
        "Number of particles must be <= 1 million (stack size limit)"

    ########################################
    # Warn if monitoring turn-by-turn with many particle turns
    ########################################
    if turn_by_turn_monitor and n_particles * n_turns > 1E8:
        print(
            "WARNING: Tracking a large number of particle turns "
            "(n_particles * n_turns > 100 million) with "
            "turn_by_turn_monitor=True leads to high memory usage.")

    ########################################
    # Configure Settings
    ########################################
    rfsw_flag       = "RFSW;" if rfsw else "NORFSW;"
    rad_flag        = "RAD;" if rad else "NORAD;"
    radcod_flag     = "RADCOD;" if radcod else "NORADCOD;"
    radtaper_flag   = "RADTAPER;" if radtaper else ""
    fluc_flag       = "FLUC;" if fluc else "NOFLUC;"

    ########################################
    # Make the arrays a single string comma separated
    ########################################
    print("Creating particle arrays")
    x_init_str      = "{" + ", ".join([f"{x}" for x in x_init]) + "}"
    px_init_str     = "{" + ", ".join([f"{px}" for px in px_init]) + "}"
    y_init_str      = "{" + ", ".join([f"{y}" for y in y_init]) + "}"
    py_init_str     = "{" + ", ".join([f"{py}" for py in py_init]) + "}"
    zeta_init_str   = "{" + ", ".join([f"{zeta}" for zeta in zeta_init]) + "}"
    delta_init_str  = "{" + ", ".join([f"{delta}" for delta in delta_init]) + "}"

    # ########################################
    # # Wrap the arrays to avoid line limits
    # ########################################
    x_init_str      = textwrap.fill(x_init_str, width = 100)
    px_init_str     = textwrap.fill(px_init_str, width = 100)
    y_init_str      = textwrap.fill(y_init_str, width = 100)
    py_init_str     = textwrap.fill(py_init_str, width = 100)
    zeta_init_str   = textwrap.fill(zeta_init_str, width = 100)
    delta_init_str  = textwrap.fill(delta_init_str, width = 100)
    print("Particle arrays created")

    ########################################
    # Progress tracking
    ########################################
    if with_progress is True:
        with_progress = 10

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
FFS["{rfsw_flag}{rad_flag}{radcod_flag}{radtaper_flag}{fluc_flag}"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Set Maximum Number of Processors
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
NPARA   = {n_cores_max};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Load and set line
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
GetMAIN["./{lattice_filepath}"];
USE {line_name};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Set tracking parameters
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
np      = {n_particles};
turns   = {n_turns};

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Generate particles
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
xs      = {x_init_str};
pxs     = {px_init_str};
ys      = {y_init_str};
pys     = {py_init_str};
zetas   = {zeta_init_str};
deltas  = {delta_init_str};
alive   = Table[1, {{np}}];
beam    = {{1, {{xs, pxs, ys, pys, zetas, deltas, alive}}}};
"""

    if turn_by_turn_monitor and with_progress:
        sad_command += f"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Store initial beam
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r0      = beam[[2]];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Track turn by turn
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r1      = Table[
    (
        If[Mod[turn, {with_progress}] == 0, WriteString[6, "PROGRESS:", turn, "\\n"];];
        beam = TrackParticles[beam, 1, turn, turn];
        beam[[2]]
    ),
    {{turn, 1, turns}}
    ];
WriteString[6,"TRACKING COMPLETE \\n"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Merge array
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r       = Prepend[r1, r0];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Save to file
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Put[r, "temp_sad_track.dat"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""
    elif turn_by_turn_monitor and not with_progress:
        sad_command += """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Store initial beam
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r0 = beam[[2]];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Track turn by turn
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r1 = Table[
    (
        beam = TrackParticles[beam, 1, turn, turn];
        beam[[2]]
    ),
    {{turn, 1, turns}}
    ];
WriteString[6,"TRACKING COMPLETE \\n"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Merge array
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
r = Prepend[r1, r0];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Save to file
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Put[r, "temp_sad_track.dat"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""
    elif not turn_by_turn_monitor and with_progress:
        sad_command += f"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Track particles
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Do[
  beam = TrackParticles[beam, 1, turn, turn+{with_progress - 1}];
  WriteString[6, "PROGRESS:", turn+{with_progress - 1}, "\\n"];
  ,
  {{turn, 1, turns, {with_progress}}}
];
WriteString[6,"TRACKING COMPLETE \\n"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Save to file
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Put[beam[[2]], "temp_sad_track.dat"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""
    else:
        sad_command += """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Track particles
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
beam = TrackParticles[beam, 1, turns];
WriteString[6,"TRACKING COMPLETE \\n"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Save to file
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Put[beam[[2]], "temp_sad_track.dat"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    print("Writing SAD Command")
    with open("temp_sad_track.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)
    del sad_command

    ########################################
    # Set up progress bar
    ########################################
    print("Running SAD")
    if with_progress:
        progress_re = re.compile(r"PROGRESS:(\d+)")
        pbar        = tqdm(total = n_turns)

    ########################################
    # Set up process
    ########################################
    stdout_lines    = []
    start           = time.time()

    process = subprocess.Popen(
        [sad_path, "temp_sad_track.sad"],
        stdout      = subprocess.PIPE,
        stderr      = subprocess.STDOUT,
        text        = True,
        bufsize     = 1)

    ########################################
    # Run the process, reading lines for progress
    ########################################
    for line in process.stdout:                                 # type: ignore
        stdout_lines.append(line)

        if process.poll() is not None:
            raise RuntimeError(f"Subprocess died early with code {process.returncode}")

        if "TRACKING COMPLETE" in line:
            if with_progress:
                pbar.close()                                    # type: ignore
            print("SAD tracking complete, writing output file")
            break

        # Check for progress lines
        if with_progress:
            m = progress_re.search(line)                        # type: ignore
            if m:
                done    = int(m.group(1))
                pbar.n  = done                                  # type: ignore
                pbar.refresh()                                  # type: ignore

        # Timeout handling
        if time.time() - start > wall_time:
            process.kill()
            os.remove("temp_sad_track.sad")
            raise TimeoutError("SAD tracking timed out")

    ########################################
    # Check the process exits correctly
    ########################################
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Subprocess exited with error code {process.returncode}")

    ########################################
    # Load the data
    ########################################
    print("Loading output file")
    with open("temp_sad_track.dat", "r", encoding = "utf-8") as f:
        raw_output  = f.read()

    ########################################
    # Remove temporary data
    ########################################
    os.remove("temp_sad_track.sad")
    os.remove("temp_sad_track.dat")

    ########################################
    # Process the data
    ########################################
    print("Processing outputs")

    # Fix Mathematica"s ".00123" → "0.00123"
    output  = re.sub(r"(?<![\d])\.(\d+)", r"0.\1", raw_output)

    # Extract all floats in a single pass
    output  = np.fromstring(
        output.replace("{", " ").replace("}", " "),
        sep = ",")

    # Reshape
    if turn_by_turn_monitor:
        output  = output.reshape(n_turns + 1, 7, n_particles)
    else:
        output  = output.reshape(7, n_particles)

    ########################################
    # Convert to Xtrack tables
    ########################################
    # Same shape as in Xtrack: particles, turns
    if turn_by_turn_monitor:
        return {
            "x":        output[:, 0, :].T,
            "px":       output[:, 1, :].T,
            "y":        output[:, 2, :].T,
            "py":       output[:, 3, :].T,
            "zeta":     output[:, 4, :].T,
            "delta":    output[:, 5, :].T,
            "state":    output[:, 6, :].T}
    else:
        return {
            "x":        output[0, :],
            "px":       output[1, :],
            "y":        output[2, :],
            "py":       output[3, :],
            "zeta":     output[4, :],
            "delta":    output[5, :],
            "state":    output[6, :]}
