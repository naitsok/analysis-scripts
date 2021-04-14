# Analysis Sripts
A collection of analysis scripts used to automate analysis of results produced by various laboratory equipment.

The scripts are written in different programming languages and thus require different software to run.

## Micromeritics Tristar II

Automated analysis and calculation of results produced by gas adsorption-desorption to study surface areas and pore size distributions of micro and mesoporous materials. The scripts use .txt files produced by Micromeritics Tristar II 3020 (Software v3.02). The analysis can be performed on single .txt file or on the batch of .txt files located in a directory.

Two python scripts do the following:
- [parse_tristar.py](./MicromeriticsTristarII/parse_tristar.py) parses the resulting .txt files to get the data already produced by Tristar software. Saves the summary values (such as specific surface area, pore size, pore volume etc.) and data for graphs (containing e.g. sorption isotherm, pore size distribution, etc.) to separate .xlsx files. If a directory was batch processed, the summary values are collected into a single .xlsx file together with sample names, while data for graphs is kept in a separate .xlsx file for each sample.
- [calc_tristar.py](./MicromeriticsTristarII/calc_tristar.py) parses only adsorption and desorption isotherms from the .txt files. It uses isotherms then to calculate all the summary values and data for graphs according to certain theories. Specific surface area is calculated using [Brunauer–Emmett–Teller theory](https://en.wikipedia.org/wiki/BET_theory). Pore size distribution is calculated using Barrett-Joyner-Halenda analysis.


