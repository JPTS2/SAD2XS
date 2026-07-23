"""
================================================================================
Line Converter
================================================================================
SAD2XS: The unofficial Strategic Accelerator Design (SAD) to Xsuite converter

This file is part of the SAD2XS project, licensed under the Apache License Version 2.0.
See LICENSE for details.

Authors:    John P. T. Salvesen
Email:      john.salvesen@cern.ch
Date:       2026-07-23
================================================================================
"""

################################################################################
# Required Packages
################################################################################
import logging

import xtrack as xt

logger  = logging.getLogger(__name__)

################################################################################
# Component Reversal
################################################################################
def create_reversed_component(
        component:              str,
        environment:            xt.Environment,
        offset_marker_names:    frozenset[str]  = frozenset()) -> str:
    """
    Create (or identify) the reversed counterpart of one line component.

    A reversed component name always starts with `-`. For element
    types whose physics genuinely differs under reversal (Bend:
    entry/exit edge angles AND fringe fields (fint/hgap) swapped;
    UniformSolenoid: ks negated; Translation/TimeDelay/Rotation: cloned
    so the reversed line gets its own copy; Marker elements that are
    SAD OFFSET markers: identified rather than cloned, so later
    offset-marker handling can still find them by name), a genuinely
    reversed clone is created.
    Every other element type (Drift, Quadrupole, Sextupole, Octupole,
    Multipole, Cavity, plain Marker, Aperture) is direction-symmetric,
    so the `-` prefix is simply dropped and the original element
    reused.

    Parameters
    ----------
    component : str
        The reversed component name, e.g. "-QF1" (must start with `-`).
    environment : xt.Environment
        The Xsuite environment containing `component[1:]`.
    offset_marker_names : frozenset of str, optional
        Lowercase names of MARK/MONI/BEAMBEAM elements that carry a SAD
        OFFSET, used to distinguish an offset marker (identified, not
        cloned) from an ordinary marker (reused as-is). Defaults to an
        empty frozenset.

    Returns
    -------
    str
        The name to use for this component in the reversed line:
        either the original `component` (if a genuine reversed clone
        was created or identified) or `component[1:]` (if the element
        is direction-symmetric).
    """

    assert component.startswith("-"), """Component must start with "-" to be reversed"""

    # Cannot overwrite elements, so must remove and recreate
    if component in environment.element_dict:
        environment.element_dict.pop(component)

    ########################################
    # Bend
    ########################################
    if isinstance(environment.element_dict[component[1:]], xt.Bend):
        environment.new(
            name      = component,
            prototype = component[1:],
            mode      = "clone")
        environment[component].edge_entry_angle  =\
            environment[component[1:]].edge_exit_angle
        environment[component].edge_exit_angle   =\
            environment[component[1:]].edge_entry_angle
        environment[component].edge_entry_fint   =\
            environment[component[1:]].edge_exit_fint
        environment[component].edge_exit_fint    =\
            environment[component[1:]].edge_entry_fint
        environment[component].edge_entry_hgap   =\
            environment[component[1:]].edge_exit_hgap
        environment[component].edge_exit_hgap    =\
            environment[component[1:]].edge_entry_hgap

    ########################################
    # Solenoid
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.UniformSolenoid):
        environment.new(
            name      = component,
            prototype = component[1:],
            mode      = "clone")
        environment[component].ks  *= -1

    ########################################
    # Transverse Reference Shift
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.Translation):
        environment.new(
            name      = component,
            prototype = component[1:],
            mode      = "clone")
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # Longitudinal Reference Shift
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.TimeDelay):
        environment.new(
            name      = component,
            prototype = component[1:],
            mode      = "clone")
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # Rotation
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.Rotation):
        environment.new(
            name      = component,
            prototype = component[1:],
            mode      = "clone")
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # Offset Marker (Mark, Moni, BeamBeam all convert to xt.Marker)
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.Marker) \
            and component[1:].lower() in offset_marker_names:
        # Here we need the - sign on the element to ID offset markers
        environment.element_dict[component] = environment.element_dict[component[1:]]

    ########################################
    # Drift, Quadrupole, Sextupole, Octupole, Multipole, Cavity, Marker, Aperture
    ########################################
    else:
        component = component[1:]

    return component

################################################################################
# Convert Lines
################################################################################
def convert_lines(
        parsed_lattice_data:    dict,
        environment:            xt.Environment) -> None:
    """
    Build every parsed SAD LINE as an Xsuite line, handling reversals.

    Reversed line references (`-LINENAME`) are resolved in three
    passes: (1) reversed real (imported) sublines have their element
    order reversed and every component negated; (2) reversed generated
    sublines (e.g. solenoid/reference-shift/thick-cavity sub-lines,
    which are never reordered) have every component negated but keep
    their order; (3) any remaining reversed component (a single
    element, not a subline) is resolved directly via
    `create_reversed_component`. Reversed generated sublines are
    deduplicated by name, so repeated references reuse the same
    `*_reversed` line.

    Parameters
    ----------
    parsed_lattice_data : dict
        Parsed lattice data, as returned by `parse_sad_file`.
    environment : xt.Environment
        The Xsuite environment to build lines into. Must already have
        every element and any generated sub-lines (solenoids,
        reference shifts, etc.) created.

    Raises
    ------
    ValueError
        If a reversed subline reference survives both reversal passes
        (an internal-consistency check -- indicates a SAD2XS bug), or
        if any parsed line fails to convert.
    """
    ########################################
    # Get the required data
    ########################################
    parsed_lines    = parsed_lattice_data["lines"]

    offset_marker_names = {
        name.lower()
        for marker_type in ("mark", "moni", "beambeam")
        for name, marker in parsed_lattice_data["elements"].get(marker_type, {}).items()
        if "offset" in marker}

    ########################################
    # Convert lines
    ########################################
    converted_lines = []
    for line, components in parsed_lines.items():

        ########################################################################
        # Handle reversed real sublines
        ########################################################################
        for i, component in enumerate(components):

            # If the component is negative, and is one of the imported lines, it is a real subline
            if "-" in component \
                    and component[1:] in parsed_lines:

                reversed_line_name      = component[1:] + "_reversed"
                reversed_line_elements  = environment.lines[component[1:]].element_names

                # If it is a real subline, reverse the order of the elements
                reversed_line_elements  = list(reversed(reversed_line_elements))

                # Negate the individual elements
                reversed_line_elements  = [f"-{elem}" for elem in reversed_line_elements]

                reverse_handled_components  = []
                for component in reversed_line_elements:
                    component   = create_reversed_component(component, environment, offset_marker_names)
                    reverse_handled_components.append(component)

                environment.new_line(
                    name        = reversed_line_name,
                    components  = reverse_handled_components)

                components[i] = reversed_line_name

        ########################################################################
        # Handle reversed generated sublines
        ########################################################################
        for i, component in enumerate(components):

            # Line and not from the importer: generated line
            # This is done to handle solenoids, ref shifts, thick cavities etc
            if "-" in component \
                    and component[1:] not in parsed_lines \
                    and component[1:] in environment.lines:
                # Checks for:
                #   - negative sign
                #   - The line is generated, not imported (parsed lines)
                #   - The line exists in the environment (to be reversed)

                reversed_line_name      = component[1:] + "_reversed"

                # Check if the line hasn't already been reversed (duplicate element)
                if reversed_line_name in environment.lines:
                    components[i] = reversed_line_name
                    continue

                reversed_line_elements  = environment.lines[component[1:]].element_names

                # If it is a generated subline, do not reverse the order of the elements
                # Just negate the individual elements
                reversed_line_elements  = [f"-{elem}" for elem in reversed_line_elements]

                reverse_handled_components  = []
                for component in reversed_line_elements:
                    component   = create_reversed_component(component, environment, offset_marker_names)
                    reverse_handled_components.append(component)

                environment.new_line(
                    name        = reversed_line_name,
                    components  = reverse_handled_components)

                components[i] = reversed_line_name

        ########################################################################
        # Handle other reversed components
        ########################################################################
        reverse_handled_components  = []
        for component in components:

            if "-" in component:
                # Reversed sublines were replaced by their *_reversed lines in
                # the passes above; a remaining line reference here means that
                # replacement logic missed a case.
                if component[1:] in environment.lines:
                    raise ValueError(
                        f"""Reversed subline "{component}" in line "{line}" """
                        "survived the subline reversal passes. This is a "
                        "SAD2XS internal error: please report it with the "
                        "lattice file.")
                reverse_handled_components.append(
                    create_reversed_component(component, environment, offset_marker_names))
            else:
                reverse_handled_components.append(component)

        environment.new_line(
            name        = line,
            components  = reverse_handled_components)
        converted_lines.append(line)

    if len(converted_lines) < len(parsed_lines):
        unconverted = sorted(
            line for line in parsed_lines if line not in converted_lines)
        raise ValueError(
            f"Converted {len(converted_lines)} lines out of {len(parsed_lines)}. "
            f"Unconverted: {unconverted}")

    logger.info(f"Converted {len(converted_lines)} lines")
