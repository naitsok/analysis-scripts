# The script is used to perform analysis of XRF spectra measured by
# Olympus Delta XRF (https://www.olympus-ims.com/en/xrf-xrd/delta-handheld/delta-prof/).
# The measurement is done for powder samples which are fixed on the XRF
# device using a custom 3D printed plastic holder(s). Several holders can be used in one
# series of measurements, which should be specified in the command line arguments.

# The analysis is based on calculating calibration for a certain metal, 
# and calculating the amount of metal in the samples with unknown amount.

import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scipy.signal import savgol_filter
from element_content.element_data import get_elements

##########
### Section with common vairables related to spectra file and measurements
##########
# CSV contains first column which has titles of rows
TITLE_COL = 1
# number of beams in the XRF measurement. 3 for Olympus Delta XRF
NUM_BEAMS = 3
# number of measurement repeats. Usually 3 is done
NUM_REPEATS = 3
# row for number of data points in spectrum
NUM_DATA_ROW = 4


def get_spectrum(spectra: pd.DataFrame, # dataframe with all spectra (loaded CSV file)
                 spectrum_num: int, # one based index of sample spectrum to take
                 repeat_num: int, # one based measurement repeat number for the sample spectrum
                 beam_num: int, # one based measurent beam number  for the sample spectrum
                 num_repeats=NUM_REPEATS, # total number of repeats for each sample
                 num_beams=NUM_BEAMS, # total number of beams for each sample
                 title_col=TITLE_COL, # indicated if title column (first one) is present in CSV
                 skip_XRF_calibration=True): # to skip first spectrum in CSV which is usually mandatory calibration for device
    # caluculate column index which is for spectrum to get
    spectrum_num -= 1
    repeat_num -= 1
    beam_num -= 1
    spectrum_num = title_col + int(skip_XRF_calibration) + num_repeats * spectrum_num * num_beams + repeat_num + beam_num
    print('Selected spectrum number: ', spectrum_num)
    # get number of data points in spectrum measured
    num_points = int(spectra.iloc[NUM_DATA_ROW, spectrum_num])
    y_spectrum = spectra.iloc[-num_points:, spectrum_num].to_numpy()
    return y_spectrum


class MetalContentParser(argparse.ArgumentParser):
    '''Class to perform parsing the input arguments and do additional checks of the input data.'''
    
    def error(self, message):
        super().error(message)

    def parse_args(self):
        args = super().parse_args()
        # get the number of spectra from CSV file
        args.spectra = pd.read_csv(args.spectra, encoding=args.encoding, delimiter='\t')
        # get elements
        args.elements_data = get_elements()
        # convert values with spectral data to int
        args.spectra.iloc[-2048:, TITLE_COL:] = args.spectra.iloc[-2048:, TITLE_COL:].astype(int)
        # calcualte the x axis; it is from 0 to 41 keV; there are 2048 points in each spectrum
        x_keV = np.linspace(0, 41, num=2048) 
        print(args.spectra.shape)
        
        # get lists from strings
        if args.element_amounts:
            # no float conversion here because some of metal amounts can be empty string
            args.element_amounts = [x.strip() for x in args.element_amounts.split(',')]
        if args.holders:
            args.holders = [int(x.strip()) for x in args.holders.split(',')]
        if args.elements:
            args.elements = [x.strip() for x in args.elements.split(',')]
        if args.powder_weights:
            args.powder_weights = [float(x.strip()) for x in args.powder_weights.split(',')]
        if args.labels:
            args.labels = [x.strip() for x in args.labels.split(',')]
        # Get beams and check they are correct
        if args.num_beams == 0:
            # get it from specta. 0 is first row in dataframe which is ExposureNum
            args.num_beams = args.spectra.iloc[0, TITLE_COL:].astype(int).max()
            print('Num beams: ', args.num_beams)
        if args.beams:
            args.beams = [int(x.strip()) for x in args.beams.split(',')]
            if args.num_beams < max(args.beams):
                self.error('number of beams in spectra is less than specified by command argument')
        # check elements are in element_content.element_data.py
        if not args.powder_element in args.elements_data.keys():
            self.error('powder element ' + args.powder_element + ' is not in ./element_content/element_data.py')
        for el in args.elements:
            if not el in args.elements_data.keys():
                self.error('element ' + el + ' selected for analysis is not in ./element_content/element_data.py')
        
        # TITLE_COL is columns with title
        num_samples = int((len(args.spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        print(num_samples)
        print(len(args.element_amounts))
        print(len(args.holders))
        print((len(args.element_amounts) + len(args.holders)) == num_samples)
        print(len(args.holders) == num_samples)
        print('Data in spectra by indicies: ', args.spectra.iloc[0, 0], args.spectra.iloc[0, 3], args.spectra.iloc[0, 39])
        
        
        holder_sp = get_spectrum(args.spectra, 1, 1, 2)
        sample_sp = get_spectrum(args.spectra, 5, 1, 2)
        
        plt.plot(x_keV, holder_sp)
        plt.plot(x_keV, savgol_filter(holder_sp, 17, 2))
        plt.plot(x_keV, sample_sp)
        plt.plot(x_keV, savgol_filter(sample_sp, 17, 2))
        # plt.show()
        
        if args.calibrate:
            # check that all the correct parameters for calibration are supplied
            if not args.holders:
                self.error('no holders for background subtraction were supplied for calibration')
            
            if (not ((len(args.element_amounts) + len(args.holders)) == num_samples \
                or (len(args.holders) == num_samples))):
                self.error('number of measured spectra in the CSV file does not correspond to specified holder IDs and element amounts')
        
        # check if calibration is present
        
        return args
    
    
parser = MetalContentParser(description='''Analysis of element content in powders from Olympus Delta XRF spectra.
                            Designed to primarily analyze metal content (such as Cu, Ag, Pt or Ai) in 
                            Si powders. Suitable, however for other elements as well. For now calibraiton for
                            Au is the only available.''')
parser.add_argument('spectra', metavar="spectra", type=str, 
                    help='Path to CSV file with spectra.')
parser.add_argument('-en', '--encoding', type=str, default='utf-16-le',
                    help='''Endofing for the spectra CSV file. Default: utf-16-le.''')
parser.add_argument('-pm', '--powder-mass', type=float, default=250, 
                    help='''[mg]. Mass of sample (e.g. Si) powder in mg used to prepare powders for calibration. 
                    It is the total mass of Si on which the certail metal amount was deposited.
                    The value is only needed when calibration is calculated. Default: 250.''')
parser.add_argument('-pe', '--powder-element', type=str, default='Si',
                    help='The base element in the powder, or the element of the largest content. Default is Si.')
parser.add_argument('-sk', '--skip-XRF-calibration', action='store_false',
                    help='''If present, the script will not skip the first spectum in the spectra CSV file.
                    The first spectrum typically contains initial XRF calibration spectrum,
                    which must be measured when the device is turned on.''')
parser.add_argument('-hs', '--holders', type=str, default='1,2',
                    help='''String containing comma separate values to specify the holders for samples.
                    Empty holders are always measured before samples and are at the beginning of the spectra CSV file.
                    Holders can be a string specifying only holder IDs. In that case the IDs will be iterated in a loop
                    for background correction of measured samples. Alternatively, the string can contain the IDs of 
                    holders for each spectrum in the spectra CSV file. If the string is empty, no background subtraction
                    for sample spectra are done. Example and default: "1,2".''')
parser.add_argument('-el', '--elements', type=str, default='Au',
                    help='''String containing comma separated elements to be analyzed from spectra.
                    For now only Au is supported. Later on Ag, Cu and Pt will be added.
                    Examples: "Au"; "Au,Ag".''')
parser.add_argument('-ea', '--element-amounts', type=str, default='0,0.5,1,3,5,10,15,,20,25',
                    help='''String containing comma separated values with amounts of element deposied on powder with --powder-mass.
                    Used to calculate calibration.
                    Can contain empty values to skip spectra if it is not needed for calibration.
                    Example and default value: "0,0.5,1,3,5,10,15,,20,25".''')
parser.add_argument('-sb', '--skip-background', action='store_true',
                    help='''If present, the background signal from sample holders is not subtracted from spectra.''')
parser.add_argument('-pw', '--powder-weights', type=str, default='250',
                    help='''String containing comma separated valued for weights of powders in mg.
                    If number of values is less than number of spectra in CSV file, the values are looped from the
                    beginning. Examples: "250"; "168.8,176.3,183.4".''')
parser.add_argument('-ca', '--calibrate', action='store_true',
                    help='''If prensent, the script must perform calibration. SI_MASS, element_amounts, HOLDERS, WEIGHTS,
                    and one METAL must be supplied. Use -h or --help flag to get full information.''')
parser.add_argument('-cf', '--cal-file', type=str, default='',
                    help='''JSON calibration file to use. If nothing supplied, a default one for the specified metal
                    will be selected (e.g. Au_cal.json).''')
parser.add_argument('-lb', '--labels', type=str, default='',
                    help='''Strring containing comma separated values for sample lables. If no lables are provided
                    then simple numerical IDs are given. Default is empty string.''')
parser.add_argument('-re', '--repeats', type=int, default=NUM_REPEATS,
                    help='''Number of measurement repeats for each sample. Default is 3.''')
parser.add_argument('-bs', '--beams', type=str, default='',
                    help='''String containing comma separate values for beams touse for analysis of each measurement repeat. 
                    Olympus Delta XRF performs analysis using 3 beams, and some of them might not be suitable for certain elements.
                    Default is empty string, which indicated that beams should be selected based on metal selection.''')
parser.add_argument('-nb', '--num-beams', type=int, default=0,
                    help='''Number of beams measured. See Olympus Delta XRF manual for details. Default: 3.''')


def calibrate(args: argparse.Namespace) -> np.array:
    # first deal with the powder element
    powder_int = [] # integrals for powder
    for sp_num, el_am in enumerate(args.element_amounts):
        # if element amount is empty string, then the data point should be skipped
        if el_am:
            el_am = float(el_am)
            repeats_int = []
            for rep_num in range(args.repeats):
                # for now add all the integrals for beams if more than one beam is selected
                if args.beams:
                    pass
                else:
                    # select beam number from the element data
                    powder_el = args.elements_data[args.powder_element]
                    spectrum = get_spectrum(args.spectrs, sp_num, rep_num, powder_el.beam,
                                            num_repeats=args.repeats, num_beams=args.num_beams,
                                            title_col=TITLE_COL, skip_XRF_calibration=args.skip_XRF_calibration)


if __name__ == '__main__':
    args = parser.parse_args()
    print(args)