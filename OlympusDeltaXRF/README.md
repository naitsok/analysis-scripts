## Olympus Delta XRF

Automated analysis of XRF spectra measured by [Olympus Delta XRF](https://www.olympus-ims.com/en/xrf-xrd/delta-handheld/delta-prof/). The measurement is done for powder samples which are fixed on the XRF device using a custom 3D printed plastic holder(s). Several holders can be used in one series of measurements, which should be specified in the command line arguments. The analysis is based on calculating calibration for a certain element, and calculating the amount of element in the samples with unknown amount. Use the following command to get help for using the script:

```python path/element_content.py --help```