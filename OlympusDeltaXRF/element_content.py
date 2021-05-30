# The script is used to perform analysis of XRF spectra measured by
# Olympus Delta XRF (https://www.olympus-ims.com/en/xrf-xrd/delta-handheld/delta-prof/).
# The measurement is done for powder samples which are fixed on the XRF
# device using a custom 3D printed plastic holder(s). Several holders can be used in one
# series of measurements, which should be specified in the command line arguments.

# The analysis is based on calculating calibration for a certain metal, 
# and calculating the amount of metal in the samples with unknown amount.

import argparse
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
from element_data import get_elements

##########
### Section with common vairables related to spectra file and measurements
##########
# CSV contains first column which has titles of rows
TITLE_COL = 1
# number of beams in the XRF measurement. 3 for Olympus Delta XRF
NUM_BEAMS = 3
# number of measurement repeats. Usually 3 is done
NUM_REPEATS = 3
# row for number of beams = ExposureNum
ROW_NUM_BEAMS = 0
# row for number of data points in spectrum
ROW_NUM_DATA = 4


def get_spectrum(spectra: pd.DataFrame, # dataframe with all spectra (loaded CSV file)
                 spectrum_num: int, # zero based index of sample spectrum to take
                 repeat_num: int, # zero based measurement repeat number for the sample spectrum
                 beam_num: int, # zero based measurent beam number  for the sample spectrum
                 num_repeats=NUM_REPEATS, # total number of repeats for each sample
                 num_beams=NUM_BEAMS, # total number of beams for each sample
                 title_col=TITLE_COL, # indicated if title column (first one) is present in CSV
                 skip_XRF_calibration=True) -> np.ndarray: # to skip first spectrum in CSV which is usually mandatory calibration for device
    # calculate column index which is for spectrum to get
    spectrum_num = title_col + int(skip_XRF_calibration) + num_repeats * spectrum_num * num_beams + repeat_num * num_repeats + beam_num
    print('Selected spectrum number:', spectrum_num)
    # get number of data points in spectrum measured
    num_points = int(spectra.iloc[ROW_NUM_DATA, spectrum_num])
    y_spectrum = spectra.iloc[-num_points:, spectrum_num].to_numpy()
    return y_spectrum

def fit_gauss(peak_spectrum: np.array) -> np.array:
    '''Fit XRF peak with gaussian.'''
    def gauss(x: np.array, *params) -> np.array:
        # Gaussian function with params = [baseline, A, mu, sigma] parameters
        baseline, A, mu, sigma = params
        return baseline + A * np.exp(-(x - mu)**2 / (2. * sigma**2))
    
    # inital params guess 
    p0 = [0., 1., 0., 1.]
    params, var_matrix = curve_fit(gauss, peak_spectrum[0], peak_spectrum[1], p0)
    peak_fit = gauss(peak_spectrum[0], *params)
    return np.array([peak_spectrum[0], peak_fit])


def calc_peak_ints(args: argparse.Namespace,
                   element: str,
                   spectrum_num: int) -> np.ndarray:
    '''Calculate peak integrals for element for certain spetrum number.'''
    print(element)
    # select beam number from the element data
    element = args.elements_data[element]
    repeat_ints = []
    for rep_num in range(args.repeats):
        spectrum = get_spectrum(args.spectra, spectrum_num, rep_num, element.beam,
                                num_repeats=args.repeats, num_beams=args.num_beams,
                                title_col=TITLE_COL, skip_XRF_calibration=args.skip_XRF_calibration)
        spectrum = savgol_filter(spectrum, element.filter_window, 2)
        
        # integrals for each peak
        peak_ints = []
        for peak_coords in element.int_limits:
            # get indices from x coordinate
            peak_mask = np.logical_and(args.x_keV >= peak_coords[0], args.x_keV <= peak_coords[1])
            peak = np.array([args.x_keV[peak_mask], spectrum[peak_mask]])
            # print(peak)
            try:
                fit = fit_gauss(peak)
                peak_ints.append(np.sum(fit[1]))
                if spectrum_num == 6 and rep_num == 1:
                    plt.plot(args.x_keV, spectrum)
                    plt.plot(fit[0], fit[1])
                    plt.show()
            except RuntimeError:
                print('Gauss fit failed for spectrum', spectrum_num)
                peak_ints.append(np.sum(peak[1]))
            
            print(peak_ints)
        
        repeat_ints.append(peak_ints)
    # calculate average and std for each peak for all repeats
    repeat_ints = np.array(repeat_ints)
    avgs = np.mean(repeat_ints, axis=0) # / weight, not used, see python element_content.py --help
    stds = np.std(repeat_ints, axis=0) # / weight
    print('averages for', element.name, 'for spectrum', spectrum_num, avgs)
    return avgs, stds


def calc_background(args: argparse.Namespace,
                    element: str) -> np.ndarray:
    '''Calculates background for holders which are at the beginning of
    spectra csv file.'''
    if args.skip_background:
        return np.array([]), np.array([])
    else:
        bg_avs = []
        bg_stds = []
        for i in range(args.num_holders):
            av, std = calc_peak_ints(args, element, i)
            bg_avs.append(av)
            bg_stds.append(std)

        print('bg averages', np.array(bg_avs), 'bg stds', np.array(bg_stds))
        return np.array(bg_avs), np.array(bg_stds)           


def analyze_element(element: str,
                    args: argparse.Namespace) -> np.ndarray:
    '''Analyze one element to get integrals of peaks.'''
    integrals = []
    for sp_num, el_am in enumerate(args.element_amounts):
        # get powder weights, not used, see python element_content.py --help
        weight = args.powder_weights[sp_num]
        # skip holders
        sp_num = sp_num + args.num_holders
        # if element amount is empty string, then the data point should be skipped
        
        if el_am:
            el_am = float(el_am)
            repeat_ints = []
            for rep_num in range(args.repeats):
                # select beam number from the element data
                powder_el = args.elements_data[element]
                spectrum = get_spectrum(args.spectra, sp_num, rep_num, powder_el.beam,
                                        num_repeats=args.repeats, num_beams=args.num_beams,
                                        title_col=TITLE_COL, skip_XRF_calibration=args.skip_XRF_calibration)
                spectrum = savgol_filter(spectrum, powder_el.filter_window, 2)
                
                # integrals for each peak
                peak_ints = []
                for peak_coords in powder_el.int_limits:
                    # get indices from x coordinate
                    peak_mask = np.logical_and(args.x_keV >= peak_coords[0], args.x_keV <= peak_coords[1])
                    peak = np.array([args.x_keV[peak_mask], spectrum[peak_mask]])
                    # print(peak)
                    try:
                        fit = fit_gauss(peak)
                        peak_ints.append(np.sum(fit[1]))
                        if sp_num == 6 and rep_num == 1:
                            plt.plot(args.x_keV, spectrum)
                            plt.plot(fit[0], fit[1])
                            plt.show()
                    except RuntimeError:
                        print('Gauss fit failed for spectrum', sp_num)
                        peak_ints.append(np.sum(peak[1]))
                    
                    print(peak_ints)
                
                repeat_ints.append(peak_ints)
            # calculate average and std for each peak for all repeats
            repeat_ints = np.array(repeat_ints)
            avgs = np.mean(repeat_ints, axis=0) # / weight, not used, see python element_content.py --help
            stds = np.std(repeat_ints, axis=0) # / weight
            print('averages for', powder_el.name, 'for spectrum', sp_num, avgs)


def calibrate(args: argparse.Namespace) -> np.ndarray:
    # first deal with the powder element
    powder_int = [] # integrals for powder
    for sp_num, el_am in enumerate(args.element_amounts):
        # get sample mass
        weight = args.powder_weights[sp_num]
        # skip holders
        sp_num = sp_num + args.num_holders
        # if element amount is empty string, then the data point should be skipped
        
        if el_am:
            el_am = float(el_am)
            repeat_ints = []
            for rep_num in range(args.repeats):
                # select beam number from the element data
                powder_el = args.elements_data[args.powder_element]
                spectrum = get_spectrum(args.spectra, sp_num, rep_num, powder_el.beam,
                                        num_repeats=args.repeats, num_beams=args.num_beams,
                                        title_col=TITLE_COL, skip_XRF_calibration=args.skip_XRF_calibration)
                spectrum = savgol_filter(spectrum, powder_el.filter_window, 2)
                
                # integrals for each peak
                peak_ints = []
                for peak_coords in powder_el.int_limits:
                    # get indices from x coordinate
                    peak_mask = np.logical_and(args.x_keV >= peak_coords[0], args.x_keV <= peak_coords[1])
                    peak = np.array([args.x_keV[peak_mask], spectrum[peak_mask]])
                    # print(peak)
                    try:
                        fit = fit_gauss(peak)
                        peak_ints.append(np.sum(fit[1]))
                        if sp_num == 6 and rep_num == 1:
                            plt.plot(args.x_keV, spectrum)
                            plt.plot(fit[0], fit[1])
                            plt.show()
                    except RuntimeError:
                        print('Gauss fit failed for spectrum', sp_num)
                        peak_ints.append(np.sum(peak[1]))
                    
                    print(peak_ints)
                
                repeat_ints.append(peak_ints)
            # calculate average and std for each peak for all repeats
            repeat_ints = np.array(repeat_ints)
            avgs = np.mean(repeat_ints, axis=0) # / weight, not used, see python element_content.py --help
            stds = np.std(repeat_ints, axis=0) # / weight
            print('averages for', powder_el.name, 'for spectrum', sp_num, avgs)
                
    



class MetalContentParser(argparse.ArgumentParser):
    '''Class to perform parsing the input arguments and do additional checks of the input data.'''
    
    def error(self, message):
        super().error(message)

    def parse_args(self) -> argparse.Namespace:
        args = super().parse_args()
        # get the number of spectra from CSV file
        args.spectra = pd.read_csv(args.spectra, encoding=args.encoding, delimiter='\t')
        # element data from element_data.py
        args.elements_data = get_elements()
        # get number of data points in spectrum
        num_points = int(args.spectra.iloc[ROW_NUM_DATA, TITLE_COL + int(args.skip_XRF_calibration)])
        # convert values with spectral data to int
        args.spectra.iloc[-num_points:, TITLE_COL:] = args.spectra.iloc[-num_points:, TITLE_COL:].astype(int)
        # calculate x axis
        args.x_keV = np.linspace(0, 41, num=num_points)
        print(args.spectra.shape)
        
        # further parse and check supplied arguments
        
        if args.element_amounts:
            # no float conversion here because some of metal amounts can be empty string
            args.element_amounts = [x.strip() for x in args.element_amounts.split(',')]
            
        # number of spectra in the CSV file considering beams, repeats and holders
        if args.elements:
            args.elements = [x.strip() for x in args.elements.split(',')]
            
        # Get beams from spectra file and check they are correct
        # 0 is first row in dataframe which is ExposureNum (= beam number)
        args.beams = args.spectra.iloc[0, TITLE_COL:].astype(int).unique()
        print('Beams: ', args.beams)
        args.num_beams = len(args.beams)
        # Check that there beams for elements are present in spectra
        for el in [args.powder_element] + args.elements:
            if not args.elements_data[el].beam in args.beams:
                self.error('No beam ' + str(args.elements_data[el].beam) + ' for element ' + el + ' is present in spectra CSV file')
            
        # sample labels
        if args.labels:
            args.labels = [x.strip() for x in args.labels.split(',')]
            
        # check elements are in element_content.element_data.py
        if not args.powder_element in args.elements_data.keys():
            self.error('powder element ' + args.powder_element + ' is not in ./element_content/element_data.py')
        for el in args.elements:
            if not el in args.elements_data.keys():
                self.error('element ' + el + ' selected for analysis is not in ./element_content/element_data.py')
                
        # Get beams from spectra file and check they are correct
        # 0 is first row in dataframe which is ExposureNum (= beam number)
        args.beams = args.spectra.iloc[0, TITLE_COL:].astype(int).unique()
        print('Beams: ', args.beams)
        args.num_beams = len(args.beams)
        
        # Check that there beams for elements are present in spectra
        for el in [args.powder_element] + args.elements:
            if not args.elements_data[el].beam in args.beams:
                self.error('No beam ' + str(args.elements_data[el].beam) + ' for element ' + el + ' is present in spectra CSV file')
        
        # calculating spectra and holders
        num_spectra = int((len(args.spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        
        # holders for background subtraction
        args.num_holders = 0
        if args.holders:
            args.holders = [int(x.strip()) for x in args.holders.split(',')]
            args.num_holders = len(set(args.holders))
            if args.num_holders < num_spectra:
                # augment holders in loop
                holder_idx = 0
                for i in range(args.num_holders, num_spectra):
                    args.holders.append(args.holders[holder_idx])
                    holder_idx += 1
                    if holder_idx == args.num_holders:
                        holder_idx = 0
            print('Augmented holders', args.holders)
        else:
            args.skip_background = True
                
        # weights of samples
        if args.powder_weights:
            args.powder_weights = [float(x.strip()) for x in args.powder_weights.split(',')]
            num_weights = len(args.powder_weights)
            if num_weights < num_spectra - args.num_holders:
                # augment powder weights in a loop 
                weight_idx = 0
                for i in range(args.num_holders + num_weights, num_spectra):
                    args.powder_weights.append(args.powder_weights[weight_idx])
                    weight_idx += 1
                    if weight_idx == num_weights:
                        weight_idx = 0
            print('Augmented powder weights', args.powder_weights)
        
        # TITLE_COL is columns with title
        num_samples = int((len(args.spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        print(num_samples)
        print(len(args.element_amounts))
        print(len(args.holders))
        print((len(args.element_amounts) + len(args.holders)) == num_samples)
        print(len(args.holders) == num_samples)
        print('Data in spectra by indicies: ', args.spectra.iloc[0, 0], args.spectra.iloc[0, 3], args.spectra.iloc[0, 39])
        
        
        holder_sp = get_spectrum(args.spectra, 1 -1, 1 -1, 2 -1)
        sample_sp = get_spectrum(args.spectra, 5 -1, 1 -1, 2 -1)
        
        # plt.plot(args.x_keV, holder_sp)
        # plt.plot(args.x_keV, savgol_filter(holder_sp, 17, 2))
        # plt.plot(args.x_keV, sample_sp)
        # plt.plot(args.x_keV, savgol_filter(sample_sp, 17, 2))
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
                            Au is the only available.
                            Note: the XRF spectra produce by the device do not depend on powder mass if the mass is 
                            more than 100 mg. For example, Si peak amplitude is the same independent if Si powder mass
                            is 115 or 190 mg.''')
parser.add_argument('spectra', metavar="spectra", type=str, 
                    help='Path to CSV file with spectra.')
parser.add_argument('-en', '--encoding', type=str, default='utf-16-le',
                    help='''Endofing for the spectra CSV file. Default: utf-16-le.''')
parser.add_argument('-cw', '--calib-weight', type=float, default=250, 
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
                    beginning. Not used since the measured XRF spectra do not depend on powder weight. 
                    For example, Si peak amplitude is the same independent if Si powder mass is 115 or 190 mg.
                    Examples: "250"; "168.8,176.3,183.4".''')
parser.add_argument('-ca', '--calibrate', action='store_true',
                    help='''If prensent, the script must perform calibration. CALIB_MASS, element_amounts, HOLDERS, POWDER_WEIGHTS,
                    and one METAL must be supplied. Use -h or --help flag to get full information.''')
parser.add_argument('-cf', '--cal-file', type=str, default='',
                    help='''JSON calibration file to use. If nothing supplied, a default one for the specified metal
                    will be selected (e.g. Au_cal.json).''')
parser.add_argument('-lb', '--labels', type=str, default='',
                    help='''Strring containing comma separated values for sample lables. If no lables are provided
                    then simple numerical IDs are given. Default is empty string.''')
parser.add_argument('-re', '--repeats', type=int, default=NUM_REPEATS,
                    help='''Number of measurement repeats for each sample. Default is 3.''')
# The beam to use is specified for each metal in the element_data.py
"""parser.add_argument('-bs', '--beams', type=str, default='',
                    help='''String containing comma separate values for beams touse for analysis of each measurement repeat. 
                    Olympus Delta XRF performs analysis using 3 beams, and some of them might not be suitable for certain elements.
                    Default is empty string, which indicated that beams should be selected based on metal selection.''')
parser.add_argument('-nb', '--num-beams', type=int, default=0,
                    help='''Number of beams measured. See Olympus Delta XRF manual for details. Default: 3.''')"""



if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    bg_avs, bg_stds = calc_background(args, args.powder_element)
    # calibrate(args)
    