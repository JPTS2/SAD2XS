"""
(Unofficial) SAD to XSuite Converter: Helpers
=============================================
Author(s):  John P T Salvesen
Email:      john.salvesen@cern.ch
Date:       09-10-2025
"""

################################################################################
# Section Heading Function
################################################################################
def print_section_heading(heading, mode = 'section'):
    """
    Prints a section heading with a specific format.
    Args:
        heading (str): The title of the section.
        mode (str): The mode of the heading, either 'section', 'subsection' or 'subsubsection'.
    """
    if mode == 'section':
        print("\n" + "#" * 80 + "\n" + heading + "\n" + "#" * 80)
    elif mode == 'subsection':
        print("\n" + "#" * 60 + "\n" + heading + "\n" + "#" * 60)
    elif mode == 'subsubsection':
        print("\n" + "#" * 40 + "\n" + heading + "\n" + "#" * 40)
    else:
        raise ValueError("Invalid mode. Use 'section', 'subsection' or 'subsubsection'.")