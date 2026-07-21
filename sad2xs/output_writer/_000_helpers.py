"""
================================================================================
Output Writer Helper Functions
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
# Import Packages
################################################################################
import numpy as np
import xdeps as xd
import xtrack as xt

from ..types import ConfigLike

################################################################################
# Naming
################################################################################

########################################
# Parent/Variable Name Extraction
########################################
def get_parentname(element_name: str) -> str:
    """
    Strip a replica suffix from an element name, if present.

    Repeated (cloned) elements are suffixed by Xsuite with "::0",
    "::1", etc.

    Parameters
    ----------
    element_name : str
        The element name, possibly with a "::N" replica suffix.

    Returns
    -------
    str
        `element_name` with any "::N" suffix removed.
    """
    # Assume to start that the parent name is the element name excluding replica
    parent_name    = element_name.split("::")[0]

    return parent_name

def get_variablename(element_name: str) -> str:
    """
    Get the base-element (optics-variable) name for an element.

    Strips both the "::N" replica suffix (see `get_parentname`) and
    any leading `-` reversal marker, since a reversed element shares
    its optics variables with the non-reversed original.

    Parameters
    ----------
    element_name : str
        The element name, possibly reversed and/or a replica.

    Returns
    -------
    str
        The base name used for this element's optics variables.
    """

    # Get the parent name
    parent_name     = get_parentname(element_name)

    # If the element is inverted, the variable name needs the `-` removed
    if parent_name.startswith("-"):
        variable_name   = parent_name[1:]
    else:
        variable_name   = parent_name

    return variable_name

################################################################################
# Elements for replication naming
################################################################################
def quantize_length(length: float, precision: float) -> float:
    """
    Round a length to the nearest integer multiple of `precision`.

    Base elements for replication are grouped and named by length: two
    lengths that round to the same value share a single base element,
    since no magnet is manufactured/measured to finer precision than
    this.

    Parameters
    ----------
    length : float
        The element length, in metres.
    precision : float
        The rounding precision, in metres (see
        `Config.MAGNET_LENGTH_PRECISION`).

    Returns
    -------
    float
        `length` rounded to the nearest multiple of `precision`.
    """
    return round(length / precision) * precision

def generate_magnet_for_replication_names(
        length_dict:    dict[float, list[str]],
        base_string:    str,
        precision:      float) -> list[str]:
    """
    Generate base-element names for replication, keyed by length.

    Each name is `base_string` followed by the length expressed as an
    integer number of `precision` units, zero-padded to 11 digits.

    Parameters
    ----------
    length_dict : dict
        Mapping of quantized length -> list of element names sharing
        that length (as produced by `extract_bend_information`,
        `extract_multipole_information`, etc.). Keys must already be
        quantized to `precision`.
    base_string : str
        The element-family prefix (e.g. "quad", "sext").
    precision : float
        The length quantization precision, in metres. Lengths must be
        non-negative and below 10 m at 1E-9 precision (an 11-digit
        field).

    Returns
    -------
    list of str
        One base-element name per length in `length_dict`, sorted.
    """
    names           = []
    length_values	= np.array(list(length_dict.keys()))
    length_values	= np.round(length_values / precision).astype(int)

    for length in length_values:
        name = f"{base_string}{length:011d}"
        names.append(name)
    names = sorted(names)

    return names

################################################################################
# KNL/KSL arrays to strings
################################################################################
def get_knl_string(knl_array: np.ndarray) -> str:
    """
    Format a knl/ksl array as a Python list literal, trimmed of
    trailing zeros.

    Parameters
    ----------
    knl_array : numpy.ndarray
        The integrated multipole strength array (knl or ksl).

    Returns
    -------
    str
        A string like "[1.0e+00, 0, 2.5e-01]", with any trailing run
        of zero entries omitted, or "[]" if every entry is zero.
    """
    # If all zero, just give an empty array
    if np.all(knl_array == 0):
        return "[]"

    # Otherwise, iterate through
    knl_string = "["
    for i, knl in enumerate(knl_array):

        # If there are no more knl values, close:
        if np.all(knl_array[i:] == 0):
            break

        # Fromat the knl value
        if knl == 0:
            knl_substring   = "0"
        else:
            knl_substring   = f"{knl:.24e}"

        # Append to the string
        if i == 0:
            knl_string += knl_substring
        else:
            knl_string += f", {knl_substring}"

    # Close the string
    knl_string += "]"
    return knl_string

################################################################################
# Extract Magnet Information
################################################################################

########################################
# Bends
########################################
def extract_bend_information(
        line:           xt.Line,
        line_table:     xd.table.Table,
        config:         ConfigLike) -> tuple[
            dict[float, list[str]], dict[float, list[str]], dict[float, list[str]],
            list[str], dict[str, str]]:
    """
    Collect real (h != 0) bends from a line and group them for
    replication.

    Distinguishes bends from correctors by `h != 0` (design
    curvature), then buckets each bend's base element by quantized
    length into horizontal (rot_s_rad ~ 0), vertical (rot_s_rad ~
    pi/2), or skew (any other rotation) groups. The writer classifies
    the line as-is; it does not repair or canonicalize bend
    orientation during serialization.

    Parameters
    ----------
    line : xt.Line
        The line to extract bend information from.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    tuple of (dict, dict, dict, list of str, dict)
        `(hbends, vbends, sbends, unique_bend_variables,
        bend_name_dict)`: three quantized-length -> [element name]
        dictionaries (horizontal/vertical/skew), the sorted list of
        distinct optics-variable base names, and a map from each
        unique bend's element name to its optics-variable base name.
    """

    ########################################
    # Get Bend Element information
    ########################################
    unique_bend_names           = []
    unique_bend_variables       = []

    for bend in line_table.rows[line_table.element_type == "Bend"].name:
        parentname      = get_parentname(bend)
        variablename    = get_variablename(bend)

        # Ensure the element is a bend not a corrector
        if line[parentname].h != 0:
            if parentname not in unique_bend_names:
                unique_bend_names.append(parentname)
                unique_bend_variables.append(variablename)

    bend_name_dict      = {}
    for bend_name, bend_variable in zip(unique_bend_names, unique_bend_variables):
        bend_name_dict[bend_name] = bend_variable

    unique_bend_variables       = sorted(list(set(unique_bend_variables)))

    ########################################
    # Bend Base Element information
    ########################################
    # Get the base elements to replicate: pure horizontal, vertical and skew.
    # The writer classifies the line as-is; it does not repair or canonicalize
    # bend orientation during serialization.
    hbends	= {}
    vbends  = {}
    sbends  = {}

    for bend in unique_bend_names:

        # Get the length and rotation of the bend
        length		= quantize_length(line[bend].length, config.MAGNET_LENGTH_PRECISION)
        rot_s_rad	= line[bend].rot_s_rad

        ########################################
        # Categorise H and V based on the rotation
        ########################################
        # Mapping from rotation → target dictionary
        angle_map = {
            0:               hbends,
            np.pi / 2:       vbends}

        # Try to match one of the valid angles
        angle_matched   = False
        for angle, bend_dict in angle_map.items():
            if np.isclose(rot_s_rad, angle):
                angle_matched   = True

                # insert without duplicates
                lst = bend_dict.setdefault(length, [])
                if bend not in lst:
                    lst.append(bend)
                # else: already there → skip silently
                break

        if not angle_matched:
            # → skew bend
            lst = sbends.setdefault(length, [])
            if bend not in lst:
                lst.append(bend)

    return hbends, vbends, sbends, unique_bend_variables, bend_name_dict

########################################
# Correctors
########################################
def extract_corrector_information(
        line:           xt.Line,
        line_table:     xd.table.Table,
        config:         ConfigLike) -> tuple[
            dict[float, list[str]], dict[float, list[str]], dict[float, list[str]],
            list[str], dict[str, str]]:
    """
    Collect correctors (h == 0 Bend elements) from a line and group
    them for replication.

    Distinguishes correctors from real bends by `h == 0` (no design
    curvature), then buckets each corrector's base element by
    quantized length into horizontal (rot_s_rad ~ 0), vertical
    (rot_s_rad ~ pi/2), or skew (any other rotation) groups. The
    writer classifies the line as-is; it does not repair or
    canonicalize corrector orientation during serialization.

    Parameters
    ----------
    line : xt.Line
        The line to extract corrector information from.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    tuple of (dict, dict, dict, list of str, dict)
        `(hcorrs, vcorrs, scorrs, unique_corr_variables,
        corr_name_dict)`: three quantized-length -> [element name]
        dictionaries (horizontal/vertical/skew), the sorted list of
        distinct optics-variable base names, and a map from each
        unique corrector's element name to its optics-variable base
        name.
    """

    ########################################
    # Get Corrector Element information
    ########################################
    unique_corr_names           = []
    unique_corr_variables       = []

    for corr in line_table.rows[line_table.element_type == "Bend"].name:
        parentname      = get_parentname(corr)
        variablename    = get_variablename(corr)

        # Ensure the element is a corrector, not a bend.
        if line[parentname].h == 0:
            if parentname not in unique_corr_names:
                unique_corr_names.append(parentname)
                unique_corr_variables.append(variablename)

    corr_name_dict      = {}
    for corr_name, corr_variable in zip(unique_corr_names, unique_corr_variables):
        corr_name_dict[corr_name] = corr_variable

    unique_corr_variables       = sorted(list(set(unique_corr_variables)))

    ########################################
    # corr Base Element information
    ########################################
    # Get the base elements to replicate: pure horizontal, vertical and skew.
    # The writer classifies the line as-is; it does not repair or canonicalize
    # corrector orientation during serialization.
    hcorrs	= {}
    vcorrs  = {}
    scorrs  = {}

    for corr in unique_corr_names:

        # Get the length and rotation of the corr
        length		= quantize_length(line[corr].length, config.MAGNET_LENGTH_PRECISION)
        rot_s_rad	= line[corr].rot_s_rad

        ########################################
        # Categorise H and V based on the rotation
        ########################################
        # Mapping from rotation → target dictionary
        angle_map = {
            0:               hcorrs,
            np.pi / 2:       vcorrs}

        # Try to match one of the valid angles
        angle_matched   = False
        for angle, corr_dict in angle_map.items():
            if np.isclose(rot_s_rad, angle):
                angle_matched   = True

                # insert without duplicates
                lst = corr_dict.setdefault(length, [])
                if corr not in lst:
                    lst.append(corr)
                # else: already there → skip silently
                break

        if not angle_matched:
            # → skew corr
            lst = scorrs.setdefault(length, [])
            if corr not in lst:
                lst.append(corr)

    return hcorrs, vcorrs, scorrs, unique_corr_variables, corr_name_dict

########################################
# Quadrupole/Sextupole/Octupole information
########################################
def extract_multipole_information(
        line:           xt.Line,
        line_table:     xd.table.Table,
        mode:           str,
        config:         ConfigLike) -> tuple[dict[float, list[str]], list[str]]:
    """
    Collect elements of one Xsuite type from a line, grouped by
    quantized length for replication.

    Parameters
    ----------
    line : xt.Line
        The line to extract element information from.
    line_table : xd.table.Table
        `line.get_table(attr=True)`.
    mode : str
        The Xsuite element-type name to match against
        `line_table.element_type` (e.g. "Quadrupole", "Sextupole",
        "Octupole", "Multipole", "UniformSolenoid").
    config : ConfigLike
        Converter configuration; only `MAGNET_LENGTH_PRECISION` is
        used.

    Returns
    -------
    tuple of (dict, list of str)
        `(magnets, unique_names)`: a quantized-length -> [element
        name] dictionary, and the list of distinct element names
        found (in first-seen order).
    """

    ########################################
    # Get Magnet Element information
    ########################################
    unique_names       = []
    for magnet in line_table.rows[line_table.element_type == mode].name:
        parentname      = get_parentname(magnet)
        if parentname not in unique_names:
            unique_names.append(parentname)

    ########################################
    # Magnets based on length
    ########################################
    magnets   = {}
    for magnet in unique_names:
        length		= quantize_length(line[magnet].length, config.MAGNET_LENGTH_PRECISION)
        if length not in magnets:
            magnets[length] = [magnet]
        else:
            if magnet not in magnets[length]:
                magnets[length].append(magnet)
            else:
                continue

    return magnets, unique_names

################################################################################
# Element is simple to clone
################################################################################
def check_is_simple_bend_corr(line: xt.Line, replica_name: str) -> bool:
    """
    True if a Bend/corrector element has no edge, offset, or
    combined-order field terms that would make cloning it unsafe.

    A "simple" element (zero edge angles/fdown terms/fringe fint-hgap,
    zero shift_x/shift_y, zero k1, and all-zero knl/ksl) is one whose
    full behaviour is captured by its length, k0, and rotation alone,
    so it can be safely represented by `env.new(..., mode="clone")`
    from a base element sharing those three values.

    Parameters
    ----------
    line : xt.Line
        The line containing `replica_name`.
    replica_name : str
        The element name to check.

    Returns
    -------
    bool
        True if the element is "simple" in the above sense.
    """
    is_simple = False

    if line[replica_name].edge_entry_angle == 0 and \
            line[replica_name].edge_exit_angle == 0 and \
            line[replica_name].edge_entry_angle_fdown == 0 and \
            line[replica_name].edge_exit_angle_fdown == 0 and \
            line[replica_name].edge_entry_fint == 0 and \
            line[replica_name].edge_entry_hgap == 0 and \
            line[replica_name].edge_exit_fint == 0 and \
            line[replica_name].edge_exit_hgap == 0 and \
            line[replica_name].shift_x == 0 and \
            line[replica_name].shift_y == 0 and \
            line[replica_name].k1 == 0 and \
            np.all(np.asarray(line[replica_name].knl) == 0) and \
            np.all(np.asarray(line[replica_name].ksl) == 0):
        is_simple = True

    return is_simple

def check_is_simple_quad_sext_oct(line: xt.Line, replica_name: str, mode: str) -> bool:
    """
    True if a QUAD/SEXT/OCT-typed element has no offset, rotation, or
    combined-order field terms that would make cloning it unsafe.

    A "simple" element has at most one of its normal/skew strength
    pair non-zero (never both), zero shift_x/shift_y/rot_s_rad, and
    all-zero knl/ksl, so it can be safely represented by
    `env.new(..., mode="clone")` from a base element sharing its
    length and single active strength.

    Parameters
    ----------
    line : xt.Line
        The line containing `replica_name`.
    replica_name : str
        The element name to check.
    mode : str
        The element type to check against: "Quadrupole", "Sextupole",
        or "Octupole".

    Returns
    -------
    bool
        True if the element is "simple" in the above sense. False for
        any `mode` other than the three listed.
    """
    is_simple   = False

    if mode == "Quadrupole":
        # Simple assumes only one of k1 or k1s is non-zero, no misalignments, no combined components
        if (line[replica_name].k1 * line[replica_name].k1s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0 and \
                np.all(np.asarray(line[replica_name].knl) == 0) and \
                np.all(np.asarray(line[replica_name].ksl) == 0):
            is_simple = True

    if mode == "Sextupole":
        # Simple assumes only one of k2 or k2s is non-zero, no misalignments, no combined components
        if (line[replica_name].k2 * line[replica_name].k2s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0 and \
                np.all(np.asarray(line[replica_name].knl) == 0) and \
                np.all(np.asarray(line[replica_name].ksl) == 0):
            is_simple = True

    if mode == "Octupole":
        # Simple assumes only one of k3 or k3s is non-zero, no misalignments, no combined components
        if (line[replica_name].k3 * line[replica_name].k3s) == 0 and \
                line[replica_name].shift_x == 0 and \
                line[replica_name].shift_y == 0 and \
                line[replica_name].rot_s_rad == 0 and \
                np.all(np.asarray(line[replica_name].knl) == 0) and \
                np.all(np.asarray(line[replica_name].ksl) == 0):
            is_simple = True

    return is_simple

def check_is_skew_quad_sext_oct(line: xt.Line, replica_name: str, mode: str) -> bool:
    """
    True if a QUAD/SEXT/OCT-typed element's skew strength is nonzero.

    Parameters
    ----------
    line : xt.Line
        The line containing `replica_name`.
    replica_name : str
        The element name to check.
    mode : str
        The element type to check against: "Quadrupole", "Sextupole",
        or "Octupole".

    Returns
    -------
    bool
        True if the element's skew strength (k1s/k2s/k3s, matching
        `mode`) is nonzero. False for any `mode` other than the three
        listed.
    """
    is_skew     = False

    if mode == "Quadrupole":
        if line[replica_name].k1s != 0:
            is_skew = True

    if mode == "Sextupole":
        if line[replica_name].k2s != 0:
            is_skew = True

    if mode == "Octupole":
        if line[replica_name].k3s != 0:
            is_skew = True

    return is_skew

def check_is_simple_unpowered_multipole(line: xt.Line, replica_name: str) -> bool:
    """
    True if a Multipole element carries no field and no offset/
    rotation.

    Parameters
    ----------
    line : xt.Line
        The line containing `replica_name`.
    replica_name : str
        The element name to check.

    Returns
    -------
    bool
        True if knl and ksl are all-zero and shift_x/shift_y/
        rot_s_rad are zero.
    """
    is_simple_unpowered = False

    if np.all(line[replica_name].knl == 0) and \
            np.all(line[replica_name].ksl == 0) and \
            line[replica_name].shift_x == 0 and \
            line[replica_name].shift_y == 0 and \
            line[replica_name].rot_s_rad == 0:
        is_simple_unpowered = True

    return is_simple_unpowered

def check_is_simple_solenoid(line: xt.Line, replica_name: str) -> bool:
    """
    True if a UniformSolenoid element carries no extra multipole
    field and no transverse offset/rotation beyond its ks.

    Parameters
    ----------
    line : xt.Line
        The line containing `replica_name`.
    replica_name : str
        The element name to check.

    Returns
    -------
    bool
        True if knl and ksl are all-zero and mult_shift_x/
        mult_shift_y/rot_s_rad are zero.
    """
    is_simple_unpowered = False

    if np.all(line[replica_name].knl == 0) and \
            np.all(line[replica_name].ksl == 0) and \
            line[replica_name].mult_shift_x == 0 and \
            line[replica_name].mult_shift_y == 0 and \
            line[replica_name].rot_s_rad == 0:
        is_simple_unpowered = True

    return is_simple_unpowered
