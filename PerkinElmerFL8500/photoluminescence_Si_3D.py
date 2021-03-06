# The script is used to perform analysis of phtotluminescence spectra of nanoscale Si measured by
# Perkin Elmer FL 8500 or 6500 using Spectrum FL Software
# (https://www.perkinelmer.com/product/fl-8500-with-spectrum-fl-software-n4200030).
# The measurement can be done with powder or liquid samples, with differnect filters to 
# get rid of excitation light in the emission spectra. The script combines the data measured in 3D mode,
# i.e. emission spectra is measured for each excitation wavelength. Depending on the excitation wavelengths
# and emission filters used the script combines the spectra into one graph. For example, consider the same
# sample was first measured with excitation wavelegths from 300 to 400 nm and emission filter at 430 nm, and
# then measured with excitation wavelegths from 400 to 500 nm with emission filter at 515 nm. Then the script
# will combine those measurements into one and plot relevant graphs for the combined data.

# Script works by setting sample id and the folder, where folders with measurements are located.
# These folders must start with sample id followed by '_' character with additional measurement 
# description. The folder contain the filter wavelength in nm somewhere after the '_' character.
# The folder may end with '_' followed by measurement index is case the measurement was repeated.
# However there is no way to select the exact measurement repeat, and it is selection is determined
# by the directory search function glob.glob().

import argparse
import chardet
import glob
import os
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xlsxwriter

from matplotlib import cm
from matplotlib.ticker import LinearLocator


def load_csv(meas_folder: str, encoding: str) -> pd.DataFrame:
    '''Loads the csv to pandas dataframe.'''
    csv_path = glob.glob(os.path.join(meas_folder, 'Administrator*'))[0]

    # get file encoding
    if encoding == '':
        with open(csv_path, 'rb') as raw:
            encoding = chardet.detect(raw.read())
            encoding = encoding['encoding']
        
    # open file and replace , with .
    with open(csv_path, 'r', encoding=encoding) as f:
        csv = f.read().replace(',', '.')
    with open(csv_path, 'w', encoding=encoding) as f:
        f.write(csv)
        
    # get dataframe
    meas_df = pd.read_csv(csv_path, sep=';', skiprows=1, encoding=encoding)
    meas_df.drop(meas_df.columns[len(meas_df.columns)-1], axis=1, inplace=True)
    meas_df.astype(float)
    
    return meas_df


def get_sample_data(measure_dir: str,
                   sample_id: str,
                   emission_filters: list,
                   excitation_wavelengths: list,
                   encoding: str) -> list:
    '''Get sample data for sample with sample_id, excitation wavelengths and emission filters'''
    # get all folders with specified
    all_sample_paths = [x for x in glob.glob(os.path.join(measure_dir, sample_id + '*')) if os.path.isdir(x)]
    print(all_sample_paths)
    if not all_sample_paths:
        print('error: sample with specified id was not found: ' + sample_id)
        return
    # loop through emission filters and sample paths to   
    # and select ine measurement for each filter and excitation range
    x_nm = []
    sample_data = []
    sample_excit_wls = []
    if emission_filters:
        # if there are emission filters, select measurement for each folder
        for i, ef in enumerate(emission_filters):
            meas_path = ''
            for path in all_sample_paths:
                if str(ef) in path:
                    meas_path = path
            if meas_path == '':
                # no measurement with such filter found
                print('error: no measurement for specified emission filter was found: ' + str(ef) + ' nm')
                return
            # load the sample data into dataframe
            print(f'info: using measurement {meas_path} for emission filter {ef} nm and range {excitation_wavelengths[i]}')
            meas_df = load_csv(meas_path, encoding)
            
            # select the first column which is wavelength in nm
            x_nm = meas_df.iloc[:, 0].to_numpy()
            # get excitation wavelengths from the column 
            meas_excit_wls = np.array([float(x.strip(')').strip('INT(')) for x in list(meas_df.columns[1:])])
            meas_data = meas_df.iloc[:,1:].to_numpy()
            excitation_filter_mask = ((meas_excit_wls >= excitation_wavelengths[i][0]) & (meas_excit_wls < excitation_wavelengths[i][1]))
            meas_data = meas_data[:, excitation_filter_mask]
            meas_excit_wls = meas_excit_wls[excitation_filter_mask]
            if len(sample_data) == 0:
                # sample data is empty make it not empty with meas data
                sample_data = meas_data
                sample_excit_wls = meas_excit_wls
            else:
                # sample data is not empty, so it can be joined with meas data
                sample_data = np.concatenate((sample_data, meas_data), axis=1)
                sample_excit_wls = np.concatenate((sample_excit_wls, meas_excit_wls))
    else:
        # select the last one from the all_sample_paths
        meas_df = load_csv(all_sample_paths[:-1], encoding)
        x_nm = meas_df.iloc[:, 0].to_numpy()
        sample_excit_wls = np.array([float(x.strip(')').strip('(')) for x in list(meas_df.columns[1:])])
        sample_data = meas_df.iloc[:,1:].to_numpy()
        
    
        
    return [x_nm, sample_excit_wls, sample_data]

def analyze_sample(args: argparse.Namespace):
    '''Performs analysis of the sample spectrum: subtracts background if specified and gets 
    values for the peak emission.'''
    x_nm, excit_wls, spectra = get_sample_data(args.measure_dir, args.sample_id, args.emission_filters,
                                               args.excitation_wavelengths, args.encoding)
    if args.bg_id:
        bg_x_nm, bg_excit_wls, bg_spectra = get_sample_data(args.measure_dir, 
                                                            args.bg_id, 
                                                            args.emission_filters,
                                                            args.excitation_wavelengths,
                                                            args.encoding)
        # manipulate the bg values for each excitation wavelengths
        # this is needed becuase background peak at ~830 nm is much larger 
        # then when sample is in holder and thus gives negative values.
        bg_max_idx = np.argmax(bg_spectra, axis=0)
        bg_max = np.amax(bg_spectra, axis=0)
        spectra_vals = spectra[bg_max_idx].diagonal()
        # multiply background to avoid negative values
        corr_factors = spectra_vals / bg_max
        bg_spectra = bg_spectra * corr_factors[None, :] * args.correction_factor
        
        # subtract the background from sample spectra
        spectra = spectra - bg_spectra
    
    # get the peak value of PL and the emission wavelength for each excitation wavelength
    # select data with emission wavelngth below 810 nm due to background peak at ~830 nm
    sample_data810 = spectra[x_nm <= 810, :]
    emission_max = np.amax(sample_data810, axis=0)
    # normalize to emission max
    # spectra = spectra / np.amax(emission_max)
    # emission_max = emission_max / np.amax(emission_max)
    wavelength_max = x_nm[np.argmax(sample_data810, axis=0)]
    # normalize spectra
    max_from_emission = np.stack((excit_wls, wavelength_max, emission_max), axis=1)
        
    # exporting to Excel to be further used for importing into OriginPro
    xlsx_file = os.path.join(args.measure_dir, args.sample_id + '_filters_' + '_'.join(args.emission_filters) + '_nm.xlsx')
    with xlsxwriter.Workbook(xlsx_file) as wb:
        wsh = wb.add_worksheet(args.sample_id)
        # first write column title
        wsh.write_row(0, 0, ['Emission wavelength'] + ['PL intensity'] * len(excit_wls) + 
                      ['Emission wavelength', 'Peak emission wavelength', 'Peak PL intensity'])
        # second write column units 
        wsh.write_row(1, 0, ['nm'] + ['a.u.'] * len(excit_wls) + ['nm', 'nm', 'a.u.'])
        # third, write comments
        wsh.write_row(2, 0, [f'Excitiation wavelength (nm)'] + [f'{x}' for x in excit_wls] + ['', args.sample_id, args.sample_id])
        # write the x nm column for 3D spectra
        wsh.write_column(3, 0, x_nm)
        # write 3D spectral data
        for col in range(spectra.shape[1]):
            wsh.write_column(3, col + 1, spectra[:, col])
        # write the PL maximum changes
        for col in range(max_from_emission.shape[1]):
            wsh.write_column(3, col + spectra.shape[1] + 1, max_from_emission[:, col])

    return [x_nm, excit_wls, spectra]
 
class PhotoluminescenceSi3DParser(argparse.ArgumentParser):
    '''Class to perform parsing the input arguments and do additional checks of the input data.'''
    
    def error(self, message):
        super().error(message)

    def parse_args(self) -> argparse.Namespace:
        args = super().parse_args()
        
        # parse wavelength ranges
        args.excitation_wavelengths = [[float(x.split('-')[0].strip()), float(x.split('-')[1].strip())]
                                       for x in args.excitation_wavelengths.split(',')]
        # parse emission filters
        args.emission_filters = [x.strip() for x in args.emission_filters.split(',')]
        
        # check that number of specified ranges is equal to number of emission filters
        if len(args.excitation_wavelengths) != len(args.emission_filters):
            self.error('number of excitation wavelength ranges is not equal to number of emission filters')
            
        if not args.analyze_dir and args.sample_id == '':
            # sample id must be provided if not a full dir is analyzed
            self.error('sample id must be specified when not full dir is analyzed')
            
        if args.sample_id:
            x_nm, excit_wls, spectra = analyze_sample(args)
            x_nm, excit_wls = np.meshgrid(x_nm, excit_wls)

            fig, ax = plt.subplots(subplot_kw={'projection': '3d'})

            # Plot the surface.
            surf = ax.plot_surface(x_nm, excit_wls, spectra.T, cmap=cm.coolwarm,
                                linewidth=0, antialiased=False)
            ax.set_xlabel('Emissition wavelength (nm)')
            ax.set_ylabel('Excitation wavelength (nm)')
            ax.set_zlabel('Intensity (a.u.)')

            # Customize the z axis.
            # ax.set_zlim(-1.01, 1.01)
            # ax.zaxis.set_major_locator(LinearLocator(10))
            # A StrMethodFormatter is used automatically
            # ax.zaxis.set_major_formatter('{x:.02f}')

            # Add a color bar which maps values to colors.
            fig.colorbar(surf, shrink=0.5, aspect=5)

            plt.show()
        
        return args
    
    
parser = PhotoluminescenceSi3DParser(description='''Analysis of 3D photoluminescence spactra measrued 
                                     by Perkin Elmer FL 8500 spectrometer with Spectrum FL Software.
                                     Combines the measured data in one file if the same sample was measured
                                     at differect excitation wavelengths and different emission filters.''')
parser.add_argument('measure_dir', metavar='measure_dir', type=str,
                    help='Directory where folders with measurements are located.')
parser.add_argument('-si', '--sample-id', type=str, default='',
                    help='''Sample id, that is at the beginning of folder with measurement for this sample. Not needed
                    when whole directory with measurements is analyze. Default: empty string.''')
parser.add_argument('-bg', '--bg-id', type=str, default='',
                    help='''Background id, background file must contain measruements with the same emission filters as
                    sample)s_.''')
parser.add_argument('-ad', '--analyze-dir', action='store_true',
                    help='''If present, script analyzes the whole directory with measurment and does not plot results. 
                    The repeat number is automatically taken to be the latest one.''')
parser.add_argument('-en', '--encoding', type=str, default='',
                    help='''Endofing for the spectra CSV file. If empty, script tries to detect encoding automatically. Default: "".''')
parser.add_argument('-ew', '--excitation-wavelengths', type=str, default='300-410, 410-490',
                    help='''The excitation wavelength ranges that indicate the range for which a specific emission filter is applied to.
                    Default: "300-400, 400-490". The default values indicates two ranges of excitation wavelengths which are 300 to 400 nm, 
                    and 400 to 500 nm.''')
parser.add_argument('-ef', '--emission-filters', type=str, default='430, 515',
                    help='''The emission filters in nm that were applied to each range of excitation wavelength. The number of
                    filters must match to the number of ranges. These filter values will be searched in the folder with 
                    measurement. Default: "430, 515". ''')
parser.add_argument('-cf', '--correction-factor', type=float, default=0.9,
                    help='''Correction factor to multiply background spectrum for correction of sample spectrum.''')


if __name__ == '__main__':
    args = parser.parse_args()
