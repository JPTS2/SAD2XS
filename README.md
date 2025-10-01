# SAD2XS: The (Unofficial) Strategic Accelerator Design (SAD) to Xsuite Converter
SAD2XS is a lattice conversion tool,.
The input is a SAD lattice (.sad format).
The converter outputs an Xtrack Line object, and generates a lattice and optics file.
The lattice file generates the lattice from base elements.

## Project status
This project is a **work in progress**.
Tests have been sucessfully performed for FCC-ee, the J-PARC Main Ring, the SuperKEKB electron and positron transfer lines (BTE and BTP) and more.
Tests with SuperKEKB have known issues, discussed below.

## Authors and acknowledgment
Written by John Salvesen in the context of his PhD, with working title "Interaction Point Collision Feedback for FCC-ee".

With thanks to the following for their vital support:
- To Giovanni Iadarola for his vital support of this project.
- To Katsunobu Oide and Giacomo Broggi for their discussion and expertise on SAD
- To Ghislain Roy for his support in testing across many different lattices.

With thanks also to FCCIS and EAJADE for their support and funding to enable this work.

### EAJADE
This work was partially supported by the European Union's Horizon Europe Marie Sklodowska-Curie Staff Exchanges programme under grant agreement no. 101086276.

![EAJADE Logo](README/EAJADE.png)

### FCCIS
This project has received funding from the European Union's Horizon 2020 research and innovation programme under the European Union's Horizon 2020 research and innovation programme under grant agreement No 951754.

![EU Logo](README/eu.png)
![FCC Logo](README/fcc.png)

### SAD
With thanks to all the developers of SAD.
The SAD documentation was used extensively in this comparison, available at [SAD](https://acc-physics.kek.jp/SAD/).
The version of SAD used in comparisons is Katsunobu Oide's version, available at [SAD GitHub](https://github.com/KatsOide/SAD).

### Xsuite
With thanks to all the developers of Xsuite.
The Xsuite documentation was used extensively in this comparison, available at [Xsuite](xsuite.readthedocs.io/).
The version of Xsuite used in comparisons is the latest version, available at [Xsuite GitHub](https://github.com/xsuite).


## Citing SAD2XS
No dedicated paper on SAD2XS has been published. 
To reference the use of SAD2XS, please reference the proceedings of eeFACT 2025 (publication TBD):

    "CONSISTENT REPRESENTATION OF LATTICES BETWEEN OPTICS CODE FOR FCC-ee SUPERKEKB AND MORE"
    J. Salvesen, G. Iadarola, G. Broggi, H. Sugimoto, K. Oide, G. Roy, A. Oeftiger

## License
This project is liscensed under the Apache License Version 2.0

[![License](https://img.shields.io/github/license/JPTS2/sad2xs)](https://github.com/JPTS2/sad2xs/blob/main/LICENSE)


## PyPI Version
The converter is available as a package on PyPI at https://pypi.org/project/sad2xs/

[![PyPI version](https://img.shields.io/pypi/v/sad2xs)](https://pypi.org/project/sad2xs/)

## Support
For any issues with the converter, please in the first instance raise an issue directly on GitHub.

For any further discussion, please contact john.salvesen@cern.ch with queries.

## Known Issues
There are some physics differences in the modelling of SAD and Xsuite that result in imperfect conversion of optical lattices.
The major known effects are detailed here.

### Fringe Import
SAD features additional fringe parameters (F1, F2) for specifying the lengrth of the inbound and outbound fringe.
This feature is not equivalently available in Xsuite.
There are therefore discrepancies on the energy loss and phase advance with highly fringed magnets (e.g. the wiggler implementation in the SuperKEKB lattices).

### Multipoles with RF
In SAD it is possible to create a multipole element with RF parameters (Voltage, Frequency, Phase).
This is not equivalently supported in Xsuite.

## Tests
A series of ongoing tests are performed to test the equivalence of SAD elements with the converted Xsuite elements.

### Test Docker (SAD Installation)
[![Docker Build](https://github.com/JPTS2/sad2xs/actions/workflows/docker-build.yml/badge.svg?branch=main)](https://github.com/JPTS2/sad2xs/actions/workflows/docker-build.yml)

### Element Tests
[![Drift](https://github.com/JPTS2/sad2xs/actions/workflows/001_drift_test.yml/badge.svg?branch=main)](https://github.com/JPTS2/sad2xs/actions/workflows/001_drift_test.yml)
[![Coordinate Transform](https://github.com/JPTS2/sad2xs/actions/workflows/002_coord_test.yml/badge.svg?branch=main)](https://github.com/JPTS2/sad2xs/actions/workflows/002_coord_test.yml)
[![Solenoid](https://github.com/JPTS2/sad2xs/actions/workflows/003_sol_test.yml/badge.svg?branch=main)](https://github.com/JPTS2/sad2xs/actions/workflows/003_sol_test.yml)
[![Reversal](https://github.com/JPTS2/sad2xs/actions/workflows/004_reversal_test.yml/badge.svg?branch=main)](https://github.com/JPTS2/sad2xs/actions/workflows/004_reversal_test.yml)