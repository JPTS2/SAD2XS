"""
(Unofficial) SAD to XSuite Converter

User Specified Element Exclusion
"""

################################################################################
# Required Packages
################################################################################
from scipy.constants import c as clight

from .._globals import print_section_heading

################################################################################
# Exclude particular elements
################################################################################
def convert_harmonic_rf(
        line,
        parsed_lattice_data:    dict,
        verbose:                bool                = False) -> dict:
    
    ########################################
    # Check if the RF uses Harmonic Number
    ########################################
    if verbose:
        print_section_heading("Checking for RF using Harmonic Number", mode = 'subsection')

    has_cavities = 'cavi' in parsed_lattice_data["elements"]
    if not has_cavities:
        print("No cavities in line")
        return line

    has_harmonic_cavities   = any(
        isinstance(v, dict) and 'harm' in v
        for v in parsed_lattice_data["elements"]["cavi"].values())
    
    if not has_harmonic_cavities:
        print("No harmonic cavities in line")
        return line

    ########################################
    # Get the revolution frequency
    ########################################
    # Really we'd like the full one, but assume the circumference one
    circumference   = line.get_length()
    speed           = clight * line.particle_ref.beta0[0]

    f_rev           = speed / circumference

    ########################################
    # Go through the elements
    ########################################
    for cavity, properties in parsed_lattice_data["elements"]["cavi"].items():
        
        is_harmonic = isinstance(properties, dict) and 'harm' in properties
        
        if is_harmonic:
            harmonic_number    = properties['harm']
            frequency          = harmonic_number * f_rev

            if verbose:
                print(f"Converting cavity {cavity} with harmonic number {harmonic_number} to frequency {frequency:.3f} Hz")

            # Update in the line
            line[cavity].frequency = frequency

    return line
