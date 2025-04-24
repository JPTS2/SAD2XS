from setuptools import setup, find_packages

setup(
    name                    = "sad2xs",
    version                 = "0.0.2",
    date                    = "24-04-2024",
    description             = "Conversion of SAD lattices to Xtrack format",
    long_description        = (
        "Python package for the conversion of particle accelerator lattices "
        "defined in Strategic Accelerator Design (SAD) to the Xtrack format "
        "(part of the Xsuite collection)"),
    author                  = "J. Salvesen, G. Iadarola",
    author_email            = "john.salvesen@cern.ch",
    url                     = "https://github.com/JPTS2/SAD2XS",
    download_url            = "TBD",
    packages                = find_packages(),
    include_package_data    = True,
    install_requires        = [
        "numpy>=1.0",
        "xtrack>=0.73"],
    license                 = 'Apache 2.0',
    project_urls            = {
        "Bug Tracker":      "https://github.com/JPTS2/SAD2XS/issues",
        "Documentation":    "https://github.com/JPTS2/SAD2XS/blob/main/README.md",
        "Source Code":      "https://github.com/JPTS2/SAD2XS",})
