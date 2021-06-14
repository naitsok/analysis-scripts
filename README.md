# Analysis Sripts
A collection of analysis scripts used to automate analysis of results produced by various laboratory equipment.

The scripts are written in different programming languages and thus require different software to run.

## Micromeritics Tristar II

Automated analysis and calculation of results produced by gas adsorption-desorption to study surface areas and pore size distributions of micro and mesoporous materials. The scripts use .txt files produced by Micromeritics Tristar II 3020 (Software v3.02). The analysis can be performed on single .txt file or on the batch of .txt files located in a directory.

Two python scripts do the following:
- [parse_tristar.py](./MicromeriticsTristarII/parse_tristar.py) parses the resulting .txt files to get the data already produced by Tristar software. Saves the summary values (such as specific surface area, pore size, pore volume etc.) and data for graphs (containing e.g. sorption isotherm, pore size distribution, etc.) to separate .xlsx files. If a directory was batch processed, the summary values are collected into a single .xlsx file together with sample names, while data for graphs is kept in a separate .xlsx file for each sample.
- [calc_tristar.py](./MicromeriticsTristarII/calc_tristar.py) parses only adsorption and desorption isotherms from the .txt files. It uses isotherms then to calculate all the summary values and data for graphs according to certain theories. Specific surface area is calculated using [Brunauer–Emmett–Teller theory](https://en.wikipedia.org/wiki/BET_theory). Pore size distribution is calculated using Barrett-Joyner-Halenda analysis.

## Olympus Delta XRF

Automated analysis of XRF spectra measured by [Olympus Delta XRF](https://www.olympus-ims.com/en/xrf-xrd/delta-handheld/delta-prof/). The measurement is done for powder samples which are fixed on the XRF device using a custom 3D printed plastic holder(s). Several holders can be used in one series of measurements, which should be specified in the command line arguments. The analysis is based on calculating calibration for a certain element, and calculating the amount of element in the samples with unknown amount. Use the following command to get help for using the script:

```python path/element_content.py --help```

Usage examples:

- Calibration: ```python .\element_content.py .\calib_spectra\Au_calib.csv -ca -pw "149.8,161.1,164,168.8,176.3,176,184,118.7,188.3,190.5" -cl "June21"```
- Analysis: ```python .\element_content.py .\data\Spectra_05_01_21.csv -pw "104.8, 107.4" -lb "Sample A, Sample B"```
