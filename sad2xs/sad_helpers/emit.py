"""
(Unofficial) SAD to XSuite Converter
"""

################################################################################
# Required Packages
################################################################################
import os
import subprocess

################################################################################
# EMIT
################################################################################
def emit_sad(
        lattice_filepath:       str,
        line_name:              str,
        radcod:                 bool        = False,
        radtaper:               bool        = False,
        additional_commands:    str         = "",
        wall_time:              int         = 30,
        sad_path:               str         = "sad") -> dict:
    """
    Generate a SAD command to compute the twiss parameters of a lattice.
    """

    ########################################
    # Configure Settings
    ########################################
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
FFS["RFSW;RAD;{radcod_flag}{radtaper_flag}NOFLUC;"];

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
! 6D Emittance Calculation
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CALC6D;
COD;
CALC;

WriteString[6, "! START EMIT"];
EMIT;
WriteString[6, "! END EMIT"];

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Close process
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
abort;
"""

    ########################################
    # Write the SAD command
    ########################################
    with open("temp_sad_emit.sad", "w", encoding = "utf-8") as f:
        f.write(sad_command)
    del sad_command

    ########################################
    # Run the process
    ########################################
    try:
        process = subprocess.run(
            [sad_path, "temp_sad_emit.sad"],
            capture_output  = True,
            text            = True,
            timeout         = wall_time,
            check           = True)
    except subprocess.TimeoutExpired:
        print(f"SAD Twiss timed out at {wall_time}s")
        if os.path.exists("temp_sad_emit.sad"):
            os.remove("temp_sad_emit.sad")
        raise
    except subprocess.CalledProcessError as e:
        print(f"SAD exited with non-zero status {e.returncode}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        if os.path.exists("temp_sad_emit.sad"):
            os.remove("temp_sad_emit.sad")
        raise
    finally:
        if os.path.exists("temp_sad_emit.sad"):
            os.remove("temp_sad_emit.sad")

    ########################################
    # Read the terminal output
    ########################################
    terminal_output = process.stdout

    ########################################
    # Process the data
    ########################################
    output = terminal_output
    output = output.split("! START EMIT")[1]
    output = output.split("! END EMIT")[0]

    ############################################################################
    # Holding pen
    ############################################################################
    # tune_shift_rad        = output.split(
    #     "Tune shift due to radiation:")[1].split("Damping partition number:")[0].strip()
    # beam_tilt              = output.split(
    #     "Beam tilt              = ")[1].split("Beam size xi")[0].strip()
    # beam_size_xi          = output.split(
    #     "Beam size xi           = ")[1].split("Beam size eta")[0].strip()
    # beam_size_eta         = output.split(
    #     "Beam size eta          = ")[1].split("Nominal spin tune")[0].strip()
    # nominal_spin_tune      = output.split(
    #     "Nominal spin tune      = ")[1].split("Polarization time")[0].strip()
    # polarization_time      = output.split(
    #     "Polarization time      = ")[1].strip()

    ############################################################################
    # Data cleaning functions
    ############################################################################
    def convert_length(string: str) -> float:
        if string.endswith(" mm"):
            return float(string.split(" mm")[0].strip()) * 1E-3
        if string.endswith(" um"):
            return float(string.split(" um")[0].strip()) * 1E-6
        if string.endswith(" nm"):
            return float(string.split(" nm")[0].strip()) * 1E-9
        if string.endswith(" m"):
            return float(string.split(" m")[0].strip())
        raise ValueError("Unknown length units")

    def convert_energy(string: str) -> float:
        if string.endswith(" TeV"):
            return float(string.split(" TeV")[0].strip()) * 1E12
        if string.endswith(" GeV"):
            return float(string.split(" GeV")[0].strip()) * 1E9
        if string.endswith(" MeV"):
            return float(string.split(" MeV")[0].strip()) * 1E6
        if string.endswith(" keV"):
            return float(string.split(" keV")[0].strip()) * 1E3
        if string.endswith(" eV"):
            return float(string.split(" eV")[0].strip())
        raise ValueError("Unknown energy units")

    def convert_frequency(string: str) -> float:
        if string.endswith(" GHz"):
            return float(string.split(" GHz")[0].strip()) * 1E9
        if string.endswith(" MHz"):
            return float(string.split(" MHz")[0].strip()) * 1E6
        if string.endswith(" kHz"):
            return float(string.split(" kHz")[0].strip()) * 1E3
        if string.endswith(" Hz"):
            return float(string.split(" Hz")[0].strip())
        raise ValueError("Unknown frequency units")

    def convert_voltage(string: str) -> float:
        if string.endswith(" GV"):
            return float(string.split(" GV")[0].strip()) * 1E9
        if string.endswith(" MV"):
            return float(string.split(" MV")[0].strip()) * 1E6
        if string.endswith(" kV"):
            return float(string.split(" kV")[0].strip()) * 1E3
        if string.endswith(" V"):
            return float(string.split(" V")[0].strip())
        raise ValueError("Unknown voltage units")

    ############################################################################
    # Data cleaning
    ############################################################################

    ########################################
    # Design Momentum
    ########################################
    design_momentum         = output.split(
        "Design momentum      P0 = ")[1].split("Revolution freq.")[0].strip()
    design_momentum = convert_energy(design_momentum)

    ########################################
    # Revolution Frequency
    ########################################
    revolution_frequency    = output.split(
        "Revolution freq.     f0 = ")[1].split("Energy loss per turn U0 = ")[0].strip()
    revolution_frequency = convert_frequency(revolution_frequency)

    ########################################
    # Energy Loss per Turn
    ########################################
    eneloss_turn            = output.split(
        "Energy loss per turn U0 = ")[1].split("Effective voltage")[0].strip()
    eneloss_turn = convert_voltage(eneloss_turn)

    ########################################
    # Effective Voltage
    ########################################
    effective_voltage        = output.split(
        "Effective voltage    Vc = ")[1].split("Equilibrium position dz = ")[0].strip()
    effective_voltage = convert_voltage(effective_voltage)

    ########################################
    # Equilibrium Zeta
    ########################################
    equilibrium_zeta         = output.split(
        "Equilibrium position dz = ")[1].split("Momentum compact.")[0].strip()
    equilibrium_zeta = convert_length(equilibrium_zeta)

    ########################################
    # Momentum compaction
    ########################################
    momentum_compaction     = output.split(
        "Momentum compact. alpha = ")[1].split("Orbit dilation       dl = ")[0].strip()
    momentum_compaction = float(momentum_compaction)

    ########################################
    # Orbit dilation
    ########################################
    orbit_dilation          = output.split(
        "Orbit dilation       dl = ")[1].split("Effective harmonic")[0].strip()
    orbit_dilation = convert_length(orbit_dilation)

    ########################################
    # Effective harmonic
    ########################################
    effective_harmonic      = output.split(
        "Effective harmonic #  h = ")[1].split("Bucket height     dV/P0 =  ")[0].strip()
    effective_harmonic = int(float(effective_harmonic))

    ########################################
    # Bucket height
    ########################################
    bucket_height           = output.split(
        "Bucket height     dV/P0 =  ")[1].split("Synchrotron frequency")[0].strip()
    bucket_height = float(bucket_height)

    ########################################
    # Synchrotron frequency
    ########################################
    synchrotron_frequency   = output.split(
        "Synchrotron frequency   = ")[1].split("\n")[0].strip()
    synchrotron_frequency = convert_frequency(synchrotron_frequency)

    ########################################
    # Imaginary Tune
    ########################################
    imag_tune              = output.split(
        "Imag.tune:")[1].split("Real tune:")[0].strip()
    imag_tune   = tuple([float(tune) for tune in imag_tune.split()])

    ########################################
    # Imaginary Tune
    ########################################
    real_tune              = output.split(
        "Real tune:")[1].split("Damping per one revolution:")[0].strip()
    real_tune   = tuple([float(tune) for tune in real_tune.split()])

    ########################################
    # Damping per Turn
    ########################################
    damping_turn          = output.split(
        "Damping per one revolution:")[1].split("Damping time (sec):")[0].strip()
    damping_turn_x = damping_turn.split("X : ")[1].split("Y : ")[0].strip()
    damping_turn_y = damping_turn.split("Y : ")[1].split("Z : ")[0].strip()
    damping_turn_z = damping_turn.split("Z : ")[1].strip()
    damping_turn   = (
        float(damping_turn_x), float(damping_turn_y), float(damping_turn_z))

    ########################################
    # Damping Time
    ########################################
    damping_time          = output.split(
        "Damping time (sec):")[1].split("Tune shift due to radiation:")[0].strip()
    damping_time_x = damping_time.split("X : ")[1].split("Y : ")[0].strip()
    damping_time_y = damping_time.split("Y : ")[1].split("Z : ")[0].strip()
    damping_time_z = damping_time.split("Z : ")[1].strip()
    damping_time   = (
        float(damping_time_x), float(damping_time_y), float(damping_time_z))

    ########################################
    # Damping Partition Number
    ########################################
    damping_partition     = output.split(
        "Damping partition number:")[1].split("\n\nEmittance X")[0].strip()
    damping_partition_x = damping_partition.split("X : ")[1].split("Y : ")[0].strip()
    damping_partition_y = damping_partition.split("Y : ")[1].split("Z : ")[0].strip()
    damping_partition_z = damping_partition.split("Z : ")[1].strip()
    damping_partition   = (
        float(damping_partition_x), float(damping_partition_y),
        float(damping_partition_z))

    ########################################
    # Emittance x
    ########################################
    gemitt_x               = output.split(
        "Emittance X            = ")[1].split("Emittance Y")[0].strip()
    gemitt_x = convert_length(gemitt_x)

    ########################################
    # Emittance y
    ########################################
    gemitt_y               = output.split(
        "Emittance Y            = ")[1].split("Emittance Z")[0].strip()
    gemitt_y = convert_length(gemitt_y)

    ########################################
    # Emittance z
    ########################################
    gemitt_z               = output.split(
        "Emittance Z            = ")[1].split("Energy spread")[0].strip()
    gemitt_z = convert_length(gemitt_z)

    ########################################
    # Energy Spread
    ########################################
    energy_spread          = output.split(
        "Energy spread          = ")[1].split("Bunch Length")[0].strip()
    energy_spread = float(energy_spread)

    ########################################
    # Bunch Length
    ########################################
    bunch_length           = output.split(
        "Bunch Length           = ")[1].split("Beam tilt")[0].strip()
    bunch_length = convert_length(bunch_length)

    ############################################################################
    # Create output dictionary
    ############################################################################
    emit_dict   = {
        "design_momentum"       : design_momentum,
        "revolution_frequency"  : revolution_frequency,
        "eneloss_turn"          : eneloss_turn,
        "effective_voltage"     : effective_voltage,
        "equilibrium_zeta"      : equilibrium_zeta,
        "momentum_compaction"   : momentum_compaction,
        "orbit_dilation"        : orbit_dilation,
        "effective_harmonic"    : effective_harmonic,
        "bucket_height"         : bucket_height,
        "synchrotron_frequency" : synchrotron_frequency,
        "imag_tune"             : imag_tune,
        "real_tune"             : real_tune,
        "damping_turn"          : damping_turn,
        "damping_time"          : damping_time,
        "damping_partition"     : damping_partition,
        "gemitt_x"              : gemitt_x,
        "gemitt_y"              : gemitt_y,
        "gemitt_z"              : gemitt_z,
        "energy_spread"         : energy_spread,
        "bunch_length"          : bunch_length}

    return emit_dict
