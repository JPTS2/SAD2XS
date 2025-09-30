# SAD2XS

## The (Unofficial) Strategic Accelerator Design (SAD) to Xsuite Converter
SAD2XS is a lattice conversion tool, taking a lattice path to a .sad lattice 
file and outputing an Xtrack Line object.

## Project status
This project is a **work in progress**.
Tests have been sucessfully performed against FCC-ee.
Tests against SuperKEKB have known issues due to the physics model differences between SAD and Xsuite.

## Authors and acknowledgment
Written by John Salvesen

With thanks for Giovanni Iadarola for his vital support of this project.

With thanks to Katsunobu Oide and Giacomo Broggi for their discussion and expertise on SAD

With thanks to Ghislain Roy for his support in testing across many different lattices.

## License
Apache License Version 2.0

## Support
Please contact john.salvesen@cern.ch with queries

## Known Issues

### Fringe Import
No import of maxwellian fringes features in SAD.
Not currently available in Xsuite