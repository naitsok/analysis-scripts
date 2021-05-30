# The script contains definition of different elements to be analyzed 
# from spectra obtained from Olympus Delta XRF
# The definition includes element name from periodic table,
# the beam number, which is the most suitable for the element,
# Savitzky-Golay filter window length
# integration limits for peak integration

import numpy as np

class ElementData:
    def __init__(self, name, beam, filter_window, int_limits) -> None:
        self.name = name # e.g. Au
        self.beam = beam # beam number: 0, 1 or 2
        self.filter_window = filter_window # odd integer, 
        # see https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html
        self.int_limits = int_limits # keV, and array of two coordinates for start and end of peak


def get_elements() -> dict:
    return {
        'Si': ElementData('Si', 2, 9, np.array([[1.5, 2],])),
        'Au': ElementData('Au', 1, 17, np.array([[9.4, 10], [10.75, 12.25]]))
    }