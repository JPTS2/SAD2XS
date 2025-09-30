"""
(Unofficial) SAD to XSuite Converter

Marker Converter
"""

################################################################################
# Required Packages
################################################################################
import numpy as np
import xtrack as xt

################################################################################
# Conversion Function
################################################################################
def convert_offset_markers(line, parsed_lattice_data):
    """
    Markers in SAD have an offset parameter that is not replicated in Xsuite
    """

    ########################################
    # Get the required data
    ########################################
    parsed_elements = parsed_lattice_data['elements']

    ########################################
    # Create output dictionary for the markers
    ########################################
    offset_marker_offsets   = {}

    ########################################
    # Get line table
    ########################################
    line.build_tracker()
    tt      = line.get_table(attr = True)
    line.discard_tracker()

    ########################################
    # Get the offsets for each marker
    ########################################
    print('Calculating offset marker positions')
    # Markers in Xsuite can come from mark, moni or beam-beam elements
    for marker_type in ['mark', 'moni', 'beambeam']:
        if marker_type in parsed_elements:
            for marker_name, marker in parsed_elements[marker_type].items():
                if 'offset' in marker:
                    offset_marker_offsets[marker_name] = marker['offset']

    ########################################
    # Get the names of the inserted markers in the line
    ########################################
    inserted_markers    = list(tt.rows[tt.element_type == 'Marker'].name)
    element_names       = list(tt.name)

    ########################################
    # Calculate intended marker locations
    ########################################
    offset_marker_locations = {}

    for marker in inserted_markers:

        base_marker     = marker.split('::')[0]

        if base_marker.startswith('-'):
            base_marker = base_marker[1:]
        
        ########################################
        # Only consider the offset markers
        ########################################
        if base_marker not in offset_marker_offsets:
            continue

        ########################################
        # Get the offset as a float
        ########################################
        offset  = offset_marker_offsets[base_marker]
        if isinstance(offset, str):
            # I think this is the source of the speed issue
            # but these can be strings with arithmetic expressions
            offset = eval(offset)

        ########################################
        # Case 1: Marker remains in the same element
        ########################################
        if 0 <= offset <= 1:
            marker_idx = element_names.index(marker)
            try:
                insert_at_ele   = element_names[marker_idx + 1]
                s_to_insert     = tt['s', insert_at_ele]
            except IndexError:  # Next element is the end of the line
                s_to_insert = tt.s[-1]
            except KeyError:    # Next element is a marker
                relative_idx = 1
                while True:
                    relative_idx += 1
                    try:
                        insert_at_ele   = element_names[marker_idx + relative_idx]
                        s_to_insert     = tt['s', insert_at_ele]
                        break
                    except KeyError:   # Next element is a marker
                        pass
                    except IndexError: # Next element is the end of the line
                        s_to_insert = tt.s[-1]
                        break

        ########################################
        # Case 2: Marker is offset to within another element
        ########################################
        else:
            # Get the index of the corresponding element
            relative_idx    = int(np.floor(offset))
            marker_idx      = element_names.index(marker)
            insert_at_ele   = element_names[marker_idx + relative_idx]

            # Get the length of the element to insert at
            insert_ele_length   = tt['length', insert_at_ele]

            # Add the fraction of element length
            s_to_insert     = tt['s', insert_at_ele] +\
                insert_ele_length * (offset % 1)

            ########################################
            # Exclusions!
            ########################################
            # TODO: Cannot slice magnets (currently unused)
            if isinstance(line[insert_at_ele], xt.Magnet):
                print("Cannot slice xt.Magnet element")
                print(f"Marker {base_marker} Ignored at {s_to_insert}")
                continue

            # TODO: Slicing solenoids causes issues
            if isinstance(line[insert_at_ele], xt.Solenoid):
                print("Slicing xt.Solenoid elements causes issues")
                print(f"Marker {base_marker} Ignored at {s_to_insert}")
                continue

        # Produce a dictionary of the s locations that markers are inserted at
        if base_marker in offset_marker_locations:
            offset_marker_locations[base_marker].append(s_to_insert)
        else:
            offset_marker_locations[base_marker] = [s_to_insert]

    ############################################################################
    # Remove the offset markers
    ############################################################################
    removed_markers = []
    for marker in inserted_markers:
        base_marker     = marker.split('::')[0]
        if base_marker.startswith('-'):
            base_marker = base_marker[1:]
        if base_marker not in offset_marker_offsets:
            continue

        if base_marker not in removed_markers:
            line.remove(base_marker)
            removed_markers.append(base_marker)

    ############################################################################
    # Return line
    ############################################################################
    return line, offset_marker_locations
