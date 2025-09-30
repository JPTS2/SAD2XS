"""
(Unofficial) SAD to XSuite Converter

Line Converter
"""

################################################################################
# Required Packages
################################################################################
import xtrack as xt

################################################################################
# Component Reversal
################################################################################
def create_reversed_component(component, environment):

    assert component.startswith('-'), "Component must start with '-' to be reversed"

    # Cannot overwrite elements, so must remove and recreate
    if component in environment.element_dict:
        environment.element_dict.pop(component)

    ########################################
    # Bend
    ########################################
    if isinstance(environment.element_dict[component[1:]], xt.Bend):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        environment[component].edge_entry_angle  =\
            environment[component[1:]].edge_exit_angle
        environment[component].edge_exit_angle   =\
            environment[component[1:]].edge_entry_angle

    ########################################
    # Solenoid
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.Solenoid):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        environment[component].ks  *= -1

    ########################################
    # Transverse Reference Shift
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.XYShift):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # Longitudinal Reference Shift
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.ZetaShift):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # X Rotation
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.XRotation):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # Y Rotation
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.YRotation):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        # Here we need the - sign on the element to ID with solenoids

    ########################################
    # S Rotation
    ########################################
    elif isinstance(environment.element_dict[component[1:]], xt.SRotation):
        environment.new(
            name    = component,
            parent  = component[1:],
            mode    = 'clone')
        # Here we need the - sign on the element to ID with solenoids

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
        environment:            xt.Environment,
        verbose:                bool                = False) -> None:
    
    ########################################
    # Get the required data
    ########################################
    parsed_lines    = parsed_lattice_data['lines']

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
            if '-' in component \
                    and component[1:] in parsed_lines:
                
                reversed_line_name      = component[1:] + '_reversed'
                reversed_line_elements  = environment.lines[component[1:]].element_names

                # If it is a real subline, reverse the order of the elements
                reversed_line_elements  = list(reversed(reversed_line_elements))

                # Negate the individual elements
                reversed_line_elements  = [f'-{elem}' for elem in reversed_line_elements]

                reverse_handled_components  = []
                for component in reversed_line_elements:
                    component   = create_reversed_component(component, environment)
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
            if '-' in component \
                    and component[1:] not in parsed_lines\
                    and component[1:] in environment.lines:
                
                reversed_line_name      = component[1:] + '_reversed'
                reversed_line_elements  = environment.lines[component[1:]].element_names
                
                # If it is a generated subline, do not reverse the order of the elements

                # Negate the individual elements
                reversed_line_elements  = [f'-{elem}' for elem in reversed_line_elements]

                reverse_handled_components  = []
                for component in reversed_line_elements:
                    component   = create_reversed_component(component, environment)
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

            if '-' in component:
                # Reversed subline
                if component[1:] in environment.lines:
                    raise ValueError("How did you get here? This should be handled above.")
                else:
                    reverse_handled_components.append(
                        create_reversed_component(component, environment))
            else:
                reverse_handled_components.append(component)

        environment.new_line(
            name        = line,
            components  = reverse_handled_components)
        converted_lines.append(line)

    if len(converted_lines) < len(parsed_lines):
        print(f"Converted {len(converted_lines)} lines out of {len(parsed_lines)}")
        raise ValueError("Not all lines could be converted. Check the input data.")
