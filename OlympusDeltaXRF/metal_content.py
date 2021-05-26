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

##########
### Section with common vairables related to spectra file and measurements
##########
# CSV contains first column which has titles of rows
TITLE_COL = 1
# number of beams in the XRF measurement. 3 for Olympus Delta XRF
NUM_BEAMS = 3
# number of measurement repeats. Usually 3 is done
NUM_REPEATS = 3


def get_spectrum(spectra: pd.DataFrame,
                 spectrum_num: int,
                 repeat_num: int,
                 beam_num: int,
                 num_repeats=NUM_REPEATS,
                 num_beams=NUM_BEAMS,
                 title_col=TITLE_COL,
                 skip_XRF_calibration=True):
    pass


class MetalContentParser(argparse.ArgumentParser):
    '''Class to perform parsing the input arguments and do additional checks of the input data.'''
    
    def error(self, message):
        super().error(message)

    def parse_args(self):
        args = super().parse_args()
        print(args)
        # get the number of spectra from CSV file
        spectra = pd.read_csv(args.spectra, encoding=args.encoding, delimiter='\t')
        # calcualte the x axis; it is from 0 to 41; there are 2048 points in each spectrum
        x_keV = np.linspace(0, 41, num=2048) 
        print(spectra.shape)
        
        # get lists from strings
        if args.metal_amounts:
            # no float conversion here because some of metal amounts can be empty string
            args.metal_amounts = [x.strip() for x in args.metal_amounts.split(',')]
        if args.holders:
            args.holders = [int(x.strip()) for x in args.holders.split(',')]
        if args.metals:
            args.metals = [x.strip() for x in args.metals.split(',')]
        if args.weights:
            args.weights = [float(x.strip()) for x in args.weights.split(',')]
        if args.labels:
            args.labels = [x.strip() for x in args.labels.split(',')]
        if args.beams:
            args.beams = [int(x.strip()) for x in args.beams.split(',')]
        else:
            # TODO: select based on metal, for now select all of them
            args.beams = [1, 2, 3]
            pass
        
        # TITLE_COL is columns with title
        num_samples = int((len(spectra.columns) - int(args.skip_XRF_calibration) - TITLE_COL) / args.repeats / args.num_beams)
        print(num_samples)
        print(len(args.metal_amounts))
        print(len(args.holders))
        print((len(args.metal_amounts) + len(args.holders)) == num_samples)
        print(len(args.holders) == num_samples)
        
        # convert values with spectral data to int
        spectra.iloc[-2048:, TITLE_COL:] = spectra.iloc[-2048:, TITLE_COL:].astype(int)
        holder_sp = spectra.iloc[-2048:, 5].to_numpy()
        sample_sp = 
        
        plt.plot(x_keV, holder_sp)
        plt.plot(x_keV, savgol_filter(holder_sp, 29, 2))
        plt.show()
        
        if args.calibrate:
            # check that all the correct parameters for calibration are supplied
            if not args.holders:
                self.error('no holders for background subtraction were supplied for calibration')
            
            if (not ((len(args.metal_amounts) + len(args.holders)) == num_samples \
                or (len(args.holders) == num_samples))):
                self.error('number of measured spectra in the CSV file does not correspond to specified holder IDs and metal amounts')
        
        # check if calibration is present
        
        return args
    
    
parser = MetalContentParser(description='''Analyze metal content in Si powders from Olympus Delta XRF spectra.
                            ''')
parser.add_argument('spectra', metavar="spectra", type=str, 
                    help='Path to CSV file with spectra.')
parser.add_argument('-en', '--encoding', type=str, default='utf-16-le',
                    help='''Endofing for the spectra CSV file. Default: utf-16-le.''')
parser.add_argument('-si', '--Si-mass', type=float, default=250, 
                    help='''[mg]. Mass of Si powder in mg used to prepare powders for calibration. 
                    It is the total mass of Si on which the certail metal amount was deposited.
                    The value is only needed when calibration is calculated. Default: 250.''')
parser.add_argument('-ma', '--metal-amounts', type=str, default='0,0.5,1,3,5,10,15,,20,25',
                    help='''String containing comma separated values with amounts of metal deposied on Si with --Si-mass.
                    Used to calculate calibration.
                    Can contain empty values to skip spectra if it is not needed for calibration.
                    Example and default value: "1,3,5,10,15,,20,25".''')
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
parser.add_argument('-me', '--metals', type=str, default='Au',
                    help='''String containing comma separated metals that are analyzed from spectra.
                    For now only Au is supported. Later on Ag, Cu and Pt will be added.
                    Examples: "Au"; "Au,Ag".''')
parser.add_argument('-sb', '--skip-background', action='store_true',
                    help='''If present, the background signal from sample holders is not subtracted from spectra.''')
parser.add_argument('-ws', '--weights', type=str, default='250',
                    help='''String containing comma separated valued for weights of samples in mg.
                    If number of values is less than number of spectra in CSV file, the values are looped from the
                    beginning. Examples: "250"; "168.8,176.3,183.4".''')
parser.add_argument('-ca', '--calibrate', action='store_true',
                    help='''If prensent, the script must perform calibration. SI_MASS, METAL_AMOUNTS, HOLDERS, WEIGHTS,
                    and one METAL must be supplied. Use -h or --help flag to get full information.''')
parser.add_argument('-cf', '--calibration_file', type=str, default='',
                    help='''JSON calibration file to use. If nothing supplied, a default one for the specified metal
                    will be selected (e.g. Au_cal.json).''')
parser.add_argument('-lb', '--labels', type=str, default='',
                    help='''Strring containing comma separated values for sample lables. If no lables are provided
                    then simple numerical IDs are given. Default is empty string.''')
parser.add_argument('-re', '--repeats', type=int, default=NUM_REPEATS,
                    help='''Number of measurement repeats for each sample. Default is 3.''')
parser.add_argument('-bs', '--beams', type=str, default='',
                    help='''String containing comma separate values for beams touse for analysis of each measurement repeat. 
                    Olympus Delta XRF performs analysis using 3 beams, and some of them might not be suitable for certain metals.
                    Default is empty string, which indicated that beams should be selected based on metal selection.''')
parser.add_argument('-nb', '--num-beams', type=int, default=NUM_BEAMS,
                    help='''Number of beams measured. See Olympus Delta XRF manual for details. Default: 3.''')

if __name__ == '__main__':
    args = parser.parse_args()
    print(args)