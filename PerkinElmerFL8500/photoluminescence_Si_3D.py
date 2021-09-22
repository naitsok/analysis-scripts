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
# The folder may end with '_' followe by measurement index is case the measurement was repeated.

import argparse
from genericpath import isdir
import chardet
import glob
import os
import re
import numpy as np
import pandas as pd


def analyze_sample(measurement_path: str,
                   sample_id: str, 
                   excitation_wavelengths: list, 
                   emission_filters: list) -> bool:
    '''Analyze one sample with sample_id, excitation wavelengths and emission filters'''
    # get all folders with specified
    all_sample_paths = [x for x in glob.glob(os.path.join(measurement_path, sample_id + '*')) if os.path.isdir(x)]
    if not all_sample_paths:
        print('error: sample with specified id was not found: ' + sample_id)
        return False
    # loop through emission filters and sample paths to   
    # and select ine measurement for each filter and excitation range
    sample_paths = []
    for path in all_sample_paths:
        sample_path = ''
        for ef in emission_filters:
            if str(ef) in path:
                sample_path = path
        if sample_path == '':
            # no measurement with such filter found
            print('error: no measurement for specified emission filter was found: ' + str(ef) + ' nm')
            return False
        sample_paths.append(sample_path)
            
        
        
    meas_name_re = re.compile(sample_id + r'[ _-\w\.\(\)]*_' + str(emission_filters[0]) + r'[ _-\w\.\(\)]*')
 
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
        args.emission_filters = [float(x.strip()) for x in args.emission_filters.split(',')]
        
        # check that number of specified ranges is equal to number of emission filters
        if len(args.excitation_wavelengths) != len(args.emission_filters):
            self.error('number of excitation wavelength ranges is not equal to number of emission filters')
            
        if not args.analyze_dir and args.sample_id == '':
            # sample id must be provided if not a full dir is analyzed
            self.error('sample if must be specified when not full dir is analyzed')
            
        # get folder with measurement for the sample
        meas_name_re = re.compile(args.sample_id + r'[ _-\w\.\(\)]*_' + str(args.emission_filters[0]) + r'[ _-\w\.\(\)]*')
            
        
        
        # load spectra file
        args.spectra_path = args.spectra
        # get file encoding
        with open(args.spectra_path, 'rb') as raw:
            encoding = chardet.detect(raw.read())
        if args.encoding == '':
            args.encoding = encoding['encoding']
        args.spectra = pd.read_csv(args.spectra_path, encoding=args.encoding, delimiter='\t')
        if args.spectra.shape[1] == 1:
            # something is wrong with delimiter
            args.spectra = pd.read_csv(args.spectra_path, encoding=args.encoding, delimiter=',')
        
        return args
    
    
parser = PhotoluminescenceSi3DParser(description='''Analysis of 3D photoluminescence spactra measrued 
                                     by Perkin Elmer FL 8500 spectrometer with Spectrum FL Software.
                                     Combines the measured data in one file if the same sample was measured
                                     at differect excitation wavelengths and different emission filters.''')
parser.add_argument('meas_dir', metavar='meas_dir', type=str,
                    help='Directory where folders with measurements are located.')
parser.add_argument('-sa', '--sample-id', type=str, default='',
                    help='''Sample id, that is at the beginning of folder with measurement for this sample. Not needed
                    when whole directory with measurements is analyze. Default: empty string.''')
parser.add_argument('-ad', '--analyze-dir', action='store_true',
                    help='''If present, script analyzes the whole directory with measurment and does not plot results. 
                    The repeat number is automatically taken to be the latest one.''')
parser.add_argument('-en', '--encoding', type=str, default='',
                    help='''Endofing for the spectra CSV file. If empty, script tries to detect encoding automatically. Default: "".''')
parser.add_argument('-ew', '--excitation-wavelengths', type=str, default='300-400, 400-500',
                    help='''The excitation wavelength ranges that indicate the range for which a specific emission filter is applied to.
                    Default: "300-400, 400-500". The default values indicates two ranges of excitation wavelengths which are 300 to 400 nm, 
                    and 400 to 500 nm.''')
parser.add_argument('-ef', '--emission-filters', type=str, default='430, 515',
                    help='''The emission filters in nm that were applied to each range of excitation wavelength. The number of
                    filters must match to the number of ranges. These filter values will be searched in the folder with 
                    measurement. Default: "430, 515". ''')
