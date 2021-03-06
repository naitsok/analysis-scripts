# The script is used to perform analysis of XRF spectra measured by
# Olympus Delta XRF (https://www.olympus-ims.com/en/xrf-xrd/delta-handheld/delta-prof/).
# The measurement is done for powder samples which are fixed on the XRF
# device using a custom 3D printed plastic holder(s). Several holders can be used in one
# series of measurements, which should be specified in the command line arguments.

# The analysis is based on calculating calibration for a certain element, 
# and calculating the amount of element in the samples with unknown amount.

import argparse
import chardet
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import sys

from datetime import datetime
from glob import glob
from scipy import stats
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
# row for time of measurement, to calculate cps instead of cumulative counts
ROW_NUM_TIME = 7 # seconds


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
    # print('Selected spectrum number:', spectrum_num)
    # get number of data points in spectrum measured
    num_points = int(spectra.iloc[ROW_NUM_DATA, spectrum_num])
    # get measurement time to caluclate cps
    meas_time = float(spectra.iloc[ROW_NUM_TIME, spectrum_num])
    y_spectrum = spectra.iloc[-num_points:, spectrum_num].to_numpy() / meas_time
    return y_spectrum

def fit_gauss(peak_spectrum: np.array) -> np.array:
    '''Fit XRF peak with gaussian.'''
    def gauss(x: np.array, *params) -> np.array:
        # Gaussian function with params = [baseline, A, mu, sigma] parameters
        baseline, A, mu, sigma = params
        return baseline + A * np.exp(-(x - mu)**2 / (2. * sigma**2))
    
    # inital params guess 
    p0 = [0., 1, 0., 1]
    x = peak_spectrum[0] / np.max(peak_spectrum[0])
    y = peak_spectrum[1] / np.max(peak_spectrum[1])
    params, cov = curve_fit(gauss, x, y, p0)
    peak_fit = gauss(x, *params) * np.max(peak_spectrum[1])
    return np.array([peak_spectrum[0], peak_fit])


def calc_peak_ints(args: argparse.Namespace,
                   element: str,
                   spectrum_num: int) -> np.ndarray:
    '''Calculate peak integrals for element for certain spetrum number.'''
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
                '''if spectrum_num == 6 and rep_num == 1:
                    plt.plot(args.x_keV, spectrum)
                    plt.plot(peak[0], peak[1])
                    plt.plot(fit[0], fit[1])
                    plt.show()'''
            except RuntimeError:
                print('Gauss fit failed for spectrum', spectrum_num)
                peak_ints.append(np.sum(peak[1]))
            
            # print(peak_ints)
        repeat_ints.append(peak_ints)
    # calculate average and std for each peak for all repeats
    repeat_ints = np.array(repeat_ints)
    avgs = np.mean(repeat_ints, axis=0) # / weight, not used, see python element_content.py --help
    stds = np.std(repeat_ints, axis=0) # / weight
    # print('averages for', element.name, 'for spectrum', spectrum_num, avgs)
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

        # print('bg averages', np.array(bg_avs), 'bg stds', np.array(bg_stds))
        return np.array(bg_avs), np.array(bg_stds)           


def analyze_element(args: argparse.Namespace,
                    element: str) -> np.ndarray:
    '''Analyze one element to get integrals of peaks.'''
    bg_avs, bg_stds = calc_background(args, element)
    # element = args.elements_data[element]
    int_avs = []
    int_stds = []
    for sp_num in range(args.num_holders, args.num_spectra):
        # weight = args.powder_weights[sp_num - args.num_holders]
        holder = args.holders[sp_num]
        avs, stds = calc_peak_ints(args, element, sp_num)
        # print('averages for sample', sp_num, 'for element', element, avs)
        if not args.skip_background:
            avs = avs - bg_avs[holder]
            stds = np.sqrt(stds**2 + bg_stds[holder]**2)
            # print('averages after bg for sample', sp_num, 'for element', element, avs)
            # print('stds after bg for sample', sp_num, 'for element', element, stds)
        int_avs.append(avs)
        int_stds.append(stds)
    return np.array(int_avs), np.array(int_stds)

def lin_int(x, a, b):
    # linear function with intercept to fit
    return a * x + b


def lin(x, a):
    # linear function without intercept to fit
    return a * x


def calibrate(args: argparse.Namespace) -> dict:
    # first deal with the powder element
    # powder_avs, powder_stds = analyze_element(args, args.powder_element)
    # get mask for samples that are meant for calibration
    cal_samples_mask = np.array(args.element_amounts) != ''
    # get x axis for samples that are meant for calibration
    args.powder_weights = args.powder_weights[cal_samples_mask]
    # calcualte the total number of Au (in umol) that are placed
    # on holder for measurement
    x_umol = np.array([float(x) for x in args.element_amounts if x != '']) # umol from agrs
    x_umol = x_umol / args.calib_weight * args.powder_weights
    x_umol = np.reshape(x_umol, (-1, ))
    x_perc = x_umol # to be converted to percent for each element as each element has molar mass
    
    # Figure
    # plots integrals with errors foreach element in row
    # if there is more than one peak for each element, then plots those peaks separately
    peak_nums = [(args.elements_data[el].int_limits.shape[0]) for el in [args.powder_element] + args.elements]
    # print('number of peaks for each element', peak_nums)
    
    plt.rcParams["figure.figsize"] = [args.fig_size * i for i in plt.rcParams["figure.figsize"]]
    fig, axs = plt.subplots(len([args.powder_element] + args.elements), max(peak_nums))
    
    # fitting results to be saved as JSON
    fitting_results = {}
    # peak integrals for powder element
    powder_avs, powder_stds = analyze_element(args, args.powder_element)
    powder_avs = powder_avs[cal_samples_mask, :]
    powder_stds = powder_stds[cal_samples_mask, :]
    
    for j, el in enumerate([args.powder_element] + args.elements):
        fitting_results[el] = []
        # umol to percent conversion coefficient
        umol_to_perc = args.elements_data[el].molar_weight / (args.calib_weight) * 1e3 / 1e4
        # x_ppm = x_umol * args.elements_data[el].molar_weight / (args.calib_weight) * 1e3
        
        el_avs, el_stds = analyze_element(args, el)
        # get rid of samples that are not meant for calibration
        el_avs = el_avs[cal_samples_mask, :]
        el_stds = el_stds[cal_samples_mask, :]
        
        # fitting for each peak on an element
        for i in range(el_avs.shape[1]):
            el_avs[:, i] = el_avs[:, i]
            el_stds[:, i] = el_stds[:, i]
            if j > 0:
                # j == 0 is powder element, needed to calculate calibrations
                # divide by the first peak integral for the powder element
                # because it is usually the case for soils and powders to analyze
                el_avs[:, i] = el_avs[:, i] / powder_avs[:, 0]
                el_stds[:, i] = np.sqrt((el_stds[:, i] / powder_avs[:, 0])**2 + \
                    (el_avs[:, i] / powder_avs[:, 0] ** 2 * powder_stds[:, 0])**2)
                x_perc = x_umol * umol_to_perc
                        
            # perform linear fitting for element (i.e. skipping args.powder_element)
            # res = stats.linregress(x_perc, el_avs[:, i].T)
            slope = 0; slope_err = 0; intercept = 0; intercept_err = 0
            y_ampl = el_avs[:, i].T
            fit_func = lin_int
            if args.skip_intercept:
                fit_func = lin
            params, cov = curve_fit(fit_func, x_perc, y_ampl)
            # calculate errors
            errs = np.sqrt(np.diag(cov))
            # get values and errors
            slope = params[0]
            slope_err = errs[0]
            if not args.skip_intercept:
                intercept = params[1]
                intercept_err = errs[1]
            # calculate r2
            ss_res = np.sum((y_ampl - fit_func(x_perc, *params)) ** 2)
            ss_tot = np.sum((y_ampl - np.mean(y_ampl)) ** 2)
            r2 = 1 - (ss_res / ss_tot)
            fitting_results[el].append({
                'peak': args.elements_data[el].int_limits[i].tolist(),
                'intercept': intercept,
                'intercept err': intercept_err,
                'slope': slope,
                'slope err': slope_err,
                # 'r2': res.rvalue**2,
                'r2': r2,
                'x perc': x_perc.tolist(),
                'umol to perc': umol_to_perc,
                'y peak area': el_avs[:, i].tolist(),
                'y peak area err': el_stds[:, i].tolist(),
                'calib weights': args.powder_weights.tolist()
                })
            
            # plotting
            axs[j, i].errorbar(x_perc, el_avs[:, i], yerr=el_stds[:, i], fmt='o')
            # axs[j, i].plot(x_perc, res.intercept + res.slope * x_perc)
            axs[j, i].plot(x_perc, fit_func(x_perc, *params))
            axs[j, i].set_title(el + ' peak [' + \
                            ', '.join(map(str, args.elements_data[el].int_limits[i])) + \
                            '] keV; r2 = ' + f'{r2:.4f}')
            axs[j, i].set_ylabel(el + ' peak area (a.u.)')
            axs[j, i].set_xlabel(el + ' amount (percent)')
            axs[j, i].legend([el, f'({slope:.3f}+/-{slope_err:.3f})*x + ({intercept:.3f}+/-{intercept_err:.3f})'])
                
    fig.tight_layout()
    # print(fitting_results)
    plt.show()
    
    # save calibrations
    for el in fitting_results.keys():
        if el != args.powder_element:
            # no need to save calibration for powder element as there is no such
            with open(os.path.join(args.calib_path, el + '_calib_' + args.calib_label + '.json'), 'w') as calib_file:
                json.dump({el: fitting_results[el]}, calib_file)
    
    return fitting_results


def analyze_content(args: argparse.Namespace) -> pd.DataFrame:
    # peak integrals for powder element
    powder_avs, powder_stds = analyze_element(args, args.powder_element)
    
    res_df = pd.DataFrame(columns=['Element'] + args.labels)
    
    for j, el in enumerate(args.elements):
        print(f'{el} calibration: {args.calib_files[el]}')
        el_avs, el_stds = analyze_element(args, el)
        with open(args.calib_files[el], 'r') as cfile:
            calib = json.load(cfile)
            
        el_res = []
        el_res_std = []
        
        for i in range(el_avs.shape[1]):
            # loop through peaks for each element
            # calibration for peak i
            calib_peak = calib[el][i]
            # calculate peaks
            el_avs[:, i] = el_avs[:, i] / powder_avs[:, 0]
            el_stds[:, i] = np.sqrt((el_stds[:, i] / powder_avs[:, 0])**2 + \
                (el_avs[:, i] / powder_avs[:, 0] ** 2 * powder_stds[:, 0])**2)
            # calculate element percentage for each peak
            intercept = calib_peak['intercept']
            intercept_err = calib_peak['intercept err']
            if args.skip_intercept:
                # Note: it is much better to use different calibration where fit 
                # was done without intercept at all
                intercept = 0
                intercept_err = 0
            el_perc = (el_avs[:, i] - intercept) / calib_peak['slope']
            el_perc_std = np.sqrt((el_stds[:, i] / calib_peak['slope'])**2 + \
                (intercept_err / calib_peak['slope'])**2 + \
                ((el_avs[:, i] - intercept) / calib_peak['slope']**2 * calib_peak['slope err'])**2)
            el_res.append(el_perc)
            el_res_std.append(el_perc_std)
        
        el_res = np.array(el_res)
        el_res_std = np.array(el_res_std)
        el_res = np.mean(el_res, axis=0)
        el_res_std = np.mean(el_res_std, axis=0)

        res_df.loc[4*j] = [el + ' perc'] + el_res.tolist()
        res_df.loc[4*j + 1] = [el + ' perc err'] + el_res_std.tolist()
        
        # el_res = el_res / calib[el][0]['umol to perc']
        # el_res_std = el_res_std / calib[el][0]['umol to perc']
        el_res = el_res * args.powder_weights * 10 / args.elements_data[el].molar_weight
        el_res_std = el_res_std * args.powder_weights * 10 / args.elements_data[el].molar_weight
        res_df.loc[4*j + 2] = [el + ' umol'] + el_res.tolist()
        res_df.loc[4*j + 3] = [el + ' umol err'] + el_res_std.tolist()
        
        print(res_df.head())
        
        res_df.to_csv(os.path.join(args.results_path, 'Result_' + \
            os.path.splitext(os.path.basename(args.spectra_path))[0] + '.csv'),
                      index=False)
        
    return res_df
 
 
class MetalContentParser(argparse.ArgumentParser):
    '''Class to perform parsing the input arguments and do additional checks of the input data.'''
    
    def error(self, message):
        super().error(message)

    def parse_args(self) -> argparse.Namespace:
        args = super().parse_args()
        # load spectra file
        args.spectra_path = args.spectra
        # get file encoding
        
        if args.encoding == '':
            with open(args.spectra_path, 'rb') as raw:
                encoding = chardet.detect(raw.read())
                args.encoding = encoding['encoding']
        args.spectra = pd.read_csv(args.spectra_path, encoding=args.encoding, delimiter='\t')
        if args.spectra.shape[1] == 1:
            # something is wrong with delimiter
            args.spectra = pd.read_csv(args.spectra_path, encoding=args.encoding, delimiter=',')
        # print(args.spectra.shape)
        # element data from element_data.py
        args.elements_data = get_elements()
        # get number of data points in spectrum
        num_points = int(args.spectra.iloc[ROW_NUM_DATA, TITLE_COL + int(args.skip_XRF_calibration)])
        # convert values with spectral data to int
        args.spectra.iloc[-num_points:, TITLE_COL:] = args.spectra.iloc[-num_points:, TITLE_COL:].astype(float)
        # calculate x axis
        args.x_keV = np.linspace(0, 41, num=num_points)
        # print(args.spectra.shape)
        
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
        # print('Beams: ', args.beams)
        args.num_beams = len(args.beams)
        # Check that there beams for elements are present in spectra
        for el in [args.powder_element] + args.elements:
            if not args.elements_data[el].beam in args.beams:
                self.error('No beam ' + str(args.elements_data[el].beam) + ' for element ' + el + ' is present in spectra CSV file')
            
        # check elements are in element_content.element_data.py
        if not args.powder_element in args.elements_data.keys():
            self.error('powder element ' + args.powder_element + ' is not in ./element_content/element_data.py')
        for el in args.elements:
            if not el in args.elements_data.keys():
                self.error('element ' + el + ' selected for analysis is not in ./element_content/element_data.py')
                
        # Get beams from spectra file and check they are correct
        # 0 is first row in dataframe which is ExposureNum (= beam number)
        args.beams = args.spectra.iloc[0, TITLE_COL:].astype(int).unique()
        # print('Beams: ', args.beams)
        args.num_beams = len(args.beams)
        
        # Check that there beams for elements are present in spectra
        for el in [args.powder_element] + args.elements:
            if not args.elements_data[el].beam in args.beams:
                self.error('No beam ' + str(args.elements_data[el].beam) + ' for element ' + el + ' is present in spectra CSV file')
        
        # calculating spectra and holders
        args.num_spectra = int((len(args.spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        
        # holders for background subtraction
        args.num_holders = 0
        if args.holders:
            # make holders zero based
            args.holders = [int(x.strip()) - 1 for x in args.holders.split(',')]
            args.num_holders = len(set(args.holders))
            if args.num_holders < args.num_spectra:
                # augment holders in loop
                holder_idx = 0
                for i in range(args.num_holders, args.num_spectra):
                    args.holders.append(args.holders[holder_idx])
                    holder_idx += 1
                    if holder_idx == args.num_holders:
                        holder_idx = 0
            # print('Augmented holders', args.holders)
        else:
            args.skip_background = True
                
        # weights of samples, not in use for now due to how the instrument works
        if args.powder_weights:
            args.powder_weights = [float(x.strip()) for x in args.powder_weights.split(',')]
            num_weights = len(args.powder_weights)
            if num_weights < args.num_spectra - args.num_holders:
                # augment powder weights in a loop 
                weight_idx = 0
                for i in range(args.num_holders + num_weights, args.num_spectra):
                    args.powder_weights.append(args.powder_weights[weight_idx])
                    weight_idx += 1
                    if weight_idx == num_weights:
                        weight_idx = 0
            args.powder_weights = np.array(args.powder_weights)
            # print('Augmented powder weights', args.powder_weights)
            
        # sample labels
        if args.labels:
            args.labels = [x.strip() for x in args.labels.split(',')]
            if len(args.labels) < args.num_spectra - args.num_holders:
                args.labels = args.labels + [f'Sample {x} {args.powder_weights[x]}' \
                    for x in range(len(args.labels), args.num_spectra - args.num_holders)]
        else:
            args.labels = [f'Sample {x} {args.powder_weights[x]}' \
                for x in range(args.num_spectra - args.num_holders)]
        
            
        # calibration
        args.calib_path = os.path.abspath(args.calib_path)
        if args.calibrate:
            # check that all the correct parameters for calibration are supplied
            if not args.holders:
                self.error('no holders for background subtraction were supplied for calibration')
            
            if (not ((len(args.element_amounts) + len(args.holders)) == args.num_spectra \
                or (len(args.holders) == args.num_spectra))):
                self.error('number of measured spectra in the CSV file does not correspond to specified holder IDs and element amounts')
                
            # calibration files
            if not os.path.exists(args.calib_path):
                os.mkdir(args.calib_path)
            if args.calib_label.lower() == '':
                args.calib_label = datetime.now().strftime('%Y%m%d')
            
        else:
            # check if calibrations existing
            args.calib_files = {}
            # print(args.calib_label)
            for el in args.elements:
                calib_files = glob(os.path.join(args.calib_path, f'{el}_calib_{args.calib_label}.json'))
                if len(calib_files) == 0:
                    # nothing found, get all calibration files for the element
                    calib_files = glob(os.path.join(args.calib_path, f'{el}_calib_{args.calib_label}*.json'))
                    if len(calib_files) == 0:
                        # Nothing found, error
                        self.error(f'calibration file for element {el} is not found')
                args.calib_files[el] = max(calib_files, key=os.path.getctime)
                
        if args.list_calibs:
            # get all files to show
            args.calib_files = glob(os.path.join(args.calib_path, f'*_calib_*.json'))
                
        # results
        if not args.results_path:
            args.results_path = os.path.dirname(args.spectra_path)
        args.results_path = os.path.abspath(args.results_path)
        if not os.path.exists(args.results_path):
            os.mkdir(args.results_path)
                
        
        
        '''# TITLE_COL is columns with title
        num_samples = int((len(args.spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        print(num_samples)
        print(len(args.element_amounts))
        print(len(args.holders))
        print((len(args.element_amounts) + len(args.holders)) == num_samples)
        print(len(args.holders) == num_samples)
        print('Data in spectra by indicies: ', args.spectra.iloc[0, 0], args.spectra.iloc[0, 3], args.spectra.iloc[0, 39])
        
        holder_sp = get_spectrum(args.spectra, 1 -1, 1 -1, 2 -1)
        sample_sp = get_spectrum(args.spectra, 5 -1, 1 -1, 2 -1)

        plt.plot(args.x_keV, holder_sp)
        plt.plot(args.x_keV, savgol_filter(holder_sp, 17, 2))
        plt.plot(args.x_keV, sample_sp)
        plt.plot(args.x_keV, savgol_filter(sample_sp, 17, 2))
        plt.show()'''
        
        return args
    
    
parser = MetalContentParser(description='''Analysis of element content in powders from Olympus Delta XRF spectra.
                            Designed to primarily analyze metal content (such as Cu, Ag, Pt or Au) in 
                            Si powders. Suitable, however for other elements as well. For now calibraiton for
                            Au is the only available.
                            To correctly use the script for another elements, the relevant data must be added to the
                            get_elements() function of element_data.py file. Contact Konstantin Tamarov for more details
                            if necessary.
                            Note: the XRF spectra produced by the device do not depend on powder mass if the mass is 
                            more than 100 mg. For example, Si peak amplitude is the same independent if Si powder mass
                            is 115 or 190 mg.''')
parser.add_argument('spectra', metavar='spectra', type=str,
                    help='Path to CSV file with spectra.')
parser.add_argument('-en', '--encoding', type=str, default='',
                    help='''Endofing for the spectra CSV file. If empty, script tries to detect encoding automatically. Default: "".''')
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
# powder weights are not needed due to how the instrument works
parser.add_argument('-pw', '--powder-weights', type=str, default='250',
                    help='''String containing comma separated valued for weights of powders in mg.
                    If number of values is less than number of spectra in CSV file, the values are looped from the
                    beginning. Not used since the measured XRF spectra do not depend on powder weight. 
                    For example, Si peak amplitude is the same independent if Si powder mass is 115 or 190 mg.
                    Examples: "250"; "168.8,176.3,183.4".''')                
parser.add_argument('-ca', '--calibrate', action='store_true',
                    help='''If prensent, the script must perform calibration. CALIB_MASS, element_amounts, HOLDERS, POWDER_WEIGHTS,
                    and one METAL must be supplied. Use -h or --help flag to get full information.''')
parser.add_argument('-cp', '--calib-path', type=str, default='./calibs/',
                    help='''Path to where to save calibration files. Default is "./calibs/".''')
parser.add_argument('-cl', '--calib-label', type=str, default='',
                    help='''The label to be added to the calibration file after ELEMENT_calib_LABEL. Element will be
                    selected based on the element to analyze. LABEL is the value specifed as parameter. The default value
                    is empty string, which means that the date of calibration will be added at the end of file.''')
parser.add_argument('-lb', '--labels', type=str, default='',
                    help='''Strring containing comma separated values for sample lables. If no lables are provided
                    then simple numerical IDs are given. Default is empty string.''')
parser.add_argument('-re', '--repeats', type=int, default=NUM_REPEATS,
                    help='''Number of measurement repeats for each sample. Default is 3.''')
parser.add_argument('-fs', '--fig-size', type=float, default=1.5,
                    help='''Figure size modifier. How much default width and height of figure will be scaled. Default: 1.5.''')
parser.add_argument('-rp', '--results-path', type=str, default='',
                    help='''Path to save results. Default: empty, save the results to the file with initial spectra.''')
parser.add_argument('-si', '--skip_intercept', action='store_true',
                    help='''If present, the intercept value from calibration is set to 0 when calculating results.''')
parser.add_argument('-lc', '--list-calibs', action='store_true',
                    help='''Display available calibration files.''')
# The beam to use is specified for each metal in the element_data.py
"""parser.add_argument('-bs', '--beams', type=str, default='',
                    help='''String containing comma separate values for beams touse for analysis of each measurement repeat. 
                    Olympus Delta XRF performs analysis using 3 beams, and some of them might not be suitable for certain elements.
                    Default is empty string, which indicated that beams should be selected based on metal selection.''')
parser.add_argument('-nb', '--num-beams', type=int, default=0,
                    help='''Number of beams measured. See Olympus Delta XRF manual for details. Default: 3.''')"""



if __name__ == '__main__':
    args = parser.parse_args()
    if args.list_calibs:
        print(f'Available calibrations at the specified path: {args.calib_path}')
        print('\n'.join([os.path.basename(x) for x in args.calib_files]))
    else:
        if args.calibrate:
            calibrate(args)
        else:
            analyze_content(args)
    