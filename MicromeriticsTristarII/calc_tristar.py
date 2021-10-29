# parses the Trisar Micrometric results files into Excel .xlsx file
# parses either a directory or a single file
# need XlsxWriter Python module (available in Anaconda by default)
# Python 3
# Usage
# python calc_tristar.py path-to-txt-file-from-tristar/path-to-dir-with-txt-files-from-tristar

import sys
import os
import glob
import re
import xlsxwriter

import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt

# all summary values list
SUMMARY_VALS = [
    'bet_A', 
    'bet_A_err',
    'bet_r',
    'total_V_user',
    'total_V_full',
    'total_A_user',
    'total_A_full',
    'max_D_user',
    'max_D_full',
    'ave_D_user',
    'ave_D_full',
    ]

# graph value list
GRAPH_VALS = [
    'D',
    'dV',
    'V',
    'dV_dD',
    'dV_dlogD',
    'dA',
    'A',
    'dA_dD',
    'dA_dlogD',
    'ads_p', 
    'ads_q', 
    'des_p',
    'des_q',
    'iso_p',
    'iso_q',
]

# header lines to be used to save in Excel
HEADER_TITLE = {
    'ads_p': 'Realtive Pressure', 
    'ads_q': 'Quantity Adsorbed', 
    'des_p': 'Realtive Pressure',
    'des_q': 'Quantity Adsorbed',
    'iso_p': 'Realtive Pressure',
    'iso_q': 'Quantity Adsorbed',
    'bet_A': 'BET surface area', 
    'bet_A_err': 'BET surface area error',
    'bet_r': 'BET fit r-value',
    'total_V_user': 'BJH Pore Volume User',
    'total_V_full': 'BJH Pore Volume',
    'total_A_user': 'BJH Pore Area User',
    'total_A_full': 'BJH Pore Area',
    'max_D_user': 'Max Pore Diameter User',
    'max_D_full': 'Max Pore Diamater',
    'ave_D_user': 'Average Pore Diameter User',
    'ave_D_full': 'Average Pore Diameter',
    'D': 'Pore Width',
    'dV': 'Differential Pore Volume',
    'V': 'Cumulative Pore Volume',
    'dV_dD': 'Pore Volume',
    'dV_dlogD': 'Pore Volume',
    'dA': 'Differentail Pore Area',
    'A': 'Cumulative Pore Area',
    'dA_dD': 'Pore Surface Area',
    'dA_dlogD': 'Pore Surface Area',
}

HEADER_UNITS = {
    'ads_p': 'p/p°', 
    'ads_q': 'cm³/g', 
    'des_p': 'p/p°',
    'des_q': 'cm³/g',
    'iso_p': 'p/p°',
    'iso_q': 'cm³/g',
    'bet_A': 'm²/g', 
    'bet_A_err': 'm²/g',
    'bet_r': '',
    'total_V_user': 'cm³/g',
    'total_V_full': 'cm³/g',
    'total_A_user': 'm²/g',
    'total_A_full': 'm²/g',
    'max_D_user': 'nm',
    'max_D_full': 'nm',
    'ave_D_user': 'nm',
    'ave_D_full': 'nm',
    'D': 'nm',
    'dV': 'cm³/g',
    'V': 'cm³/g',
    'dV_dD': 'dV/dD cm³/(nm·g)',
    'dV_dlogD': 'dV/dlog(D) cm³/(nm·g)',
    'dA': 'm²/g',
    'A': 'm²/g',
    'dA_dD': 'dA/dD m²/(nm·g)',
    'dA_dlogD': 'dA/dlog(D) m²/(nm·g)',
}


def get_sample_name(fname):
    """Gets only the sample name from the full path provided by fname"""
    return os.path.splitext(os.path.basename(fname))[0]


def parse_isoterm_branch(fname, branch):
    """Gets values for either adsorption or desorption branch of the isotherm"""

    table_beginning = r'\-\s+' + branch + r'[\s\n]+Relative Pressure[a-zA-Z°³\/\(\)\n\sі]*'

    with open(fname, encoding='utf-16-le') as file:

        # searching for table with values
        p = re.compile(table_beginning + r'[\n\s]*(((\d+(.[\de-]+)?)\s+(\d+(.[\de-]+)?)\s*\n+)*)', re.IGNORECASE)
        # get only the part with numbers to exctract them afterwards
        values_only = p.search(file.read())

        # check if values were found
        if values_only is None:
            print(table_beginning + ' was not found. Check Tristar file and/or regular expression.')
            return np.zeros([1, 2])

        # now get the values
        result_x = list()
        result_y = list()
        p = re.compile(r'(\d+(.\d+)?)\s+(\d+(.[\de-]+)?)', re.IGNORECASE)
        for iter in p.finditer(values_only.group(1)):
            result_x.append(float(iter.group(1).replace(',', '.')))
            result_y.append(float(iter.group(3).replace(',', '.')))

        return np.array([result_x, result_y]).T


def parse_isotherms(fname):
    """Parses both isotherm branches from the file."""
    ads = parse_isoterm_branch(fname, 'Adsorption')
    des = parse_isoterm_branch(fname, 'Desorption')

    # join the data to then get back ads and des isotherms
    # needed because there might be a different max pressure 
    # in ads and des branches
    ads = ads[ads[:, 0].argsort()] # sort ascending pressure
    des = des[des[:, 0].argsort()][::-1, :] # sort descending order
    iso = np.concatenate((ads, des), axis=0)
    max_pressure_idx = np.argmax(iso[:, 0])

    # return both in the descending pressure order

    return {
        'ads_p_q': iso[: max_pressure_idx + 1, :], 
        'des_p_q': iso[max_pressure_idx :, :],
        # this is for graphs
        'ads_p': iso[: max_pressure_idx + 1, 0], 
        'ads_q': iso[: max_pressure_idx + 1, 1], 
        'des_p': iso[max_pressure_idx :, 0],
        'des_q': iso[max_pressure_idx :, 1],
        'iso_p': iso[:, 0],
        'iso_q': iso[:, 1]
    }


def calc_BET(ads):
    """Calculates BET surface area and graph from adsorption branch."""
    # get the values for desired pressures BET calculation
    ads_bet = ads[(ads[:, 0] > 0.05) & (ads[:, 0] < 0.3) , :]
    ads_bet[:, 1] = 1. / (ads_bet[:, 1] * (ads_bet[:, 0]**(-1) - 1))
    # print('BET array length:', len(ads_bet))
    # print(ads_bet)

    slope, intercept, r_value, _, _ = linregress(ads_bet)
    slope_err = slope * np.sqrt((r_value**(-2) - 1) / (len(ads_bet) - 2))
    intercept_err = intercept * np.sqrt((r_value**(-2) - 1) / (len(ads_bet) - 2))

    # 4.35255551372 comes from SSA = V_m * (sigma_N2 * N_a) / V_0
    # 4.35255551372 = (sigma_N2 * N_a) / V_0
    # sigma_N2 = 16.2 Angstrom^2
    # N_a is Avogadro number
    # V_0 = 22400 cm3 / mol, molar volume of N2 gas at STP
    bet_ssa = 4.35255551372 / (slope + intercept)
    bet_ssa_err = 3 * bet_ssa * np.sqrt(slope_err**2 + intercept_err**2) / (slope + intercept)
    # print(slope, slope_err, intercept, intercept_err, r_value)
    # print(bet_ssa, bet_ssa_err)

    # plt.plot(ads_bet[:, 0], ads_bet[:, 1], 'o', label='data for BET')
    # plt.plot(ads_bet[:, 0], intercept + slope * ads_bet[:, 0], 'r', label='fitted BET')
    # plt.legend()
    # plt.show()

    return { 
        'bet_x': ads_bet[:, 0],
        'bet_y': ads_bet[:, 1],
        'bet_y_calc': intercept + slope * ads_bet[:, 0],
        'bet_A': bet_ssa,
        'bet_A_err': bet_ssa_err,
        'bet_r': r_value,
    }


def calc_BJH(iso_branch, start_pore_diam=2.5, end_pore_diam=90.):
    """Calculates BJH for adsorption or desorption branch.
        iso_brach: adsorption or desorption isotherm brach
        start_pore_diam: [nm] pores below this diameter will be 
            excluded from calulation of cumulative and average values.
        end_pore_diam: [nm] pores above this diameter will be 
            excluded from calulation of cumulative and average values."""
    # verify data is descending pressure order
    iso_branch = iso_branch[iso_branch[:, 0].argsort()][::-1, :]
    # print(iso_branch)
    radii = -0.415 / np.log10(iso_branch[:, 0])
    wall_ads_layers = np.sqrt(0.1399 / (0.034 - np.log10(iso_branch[:, 0])))

    # calculate diameters
    diameters = radii + np.roll(radii, 1) + wall_ads_layers + np.roll(wall_ads_layers, 1)
    diameters[0] = 0.
    # print(np.array([radii, wall_ads_layers, diameters]).T)

    # area and volume of pores
    helper_arr = np.zeros_like(diameters)
    diff_V = np.zeros_like(diameters)
    diff_A = np.zeros_like(diameters)
    cum_V = np.zeros_like(diameters)
    cum_A = np.zeros_like(diameters)
    dV_dD = np.zeros_like(diameters)
    dA_dD = np.zeros_like(diameters)
    dV_dlogD = np.zeros_like(diameters)
    dA_dlogD = np.zeros_like(diameters)
    
    # because these calculations depend on each other, it very difficult to figure out correct broadcast calculation
    for i in range(1, len(diameters)):
        helper_arr[i] = diff_A[i-1] / 1000 * (1 - wall_ads_layers[i] / (diameters[i]/2)) + helper_arr[i-1]

        diff_V[i] = (diameters[i] / (diameters[i]/2 - wall_ads_layers[i]))**2 * \
            (0.0015468 * (iso_branch[i-1, 1] - iso_branch[i, 1]) - (wall_ads_layers[i-1] - wall_ads_layers[i]) * helper_arr[i]) / 4
        cum_V[i] = cum_V[i-1] + diff_V[i]

        diff_A[i] = 4000 * diff_V[i] / diameters[i]        
        cum_A[i] = cum_A[i-1] + diff_A[i]

        dD = (radii[i-1] + wall_ads_layers[i-1] - radii[i] - wall_ads_layers[i])
        dV_dD[i] = diff_V[i] / dD / 2
        dA_dD[i] = diff_A[i] / dD / 2

        dlogD = (np.log10(radii[i-1]) + np.log10(wall_ads_layers[i-1]) - np.log10(radii[i]) - np.log10(wall_ads_layers[i])) / 2
        dV_dlogD[i] = diff_V[i] / dlogD
        dA_dlogD[i] = diff_A[i] / dlogD

    # print(np.array([dV_dD, dV_dlogD]).T)
    
    total_V_user = np.max(cum_V[(diameters >= start_pore_diam) & (diameters <= end_pore_diam)])
    total_A_user = np.max(cum_A[(diameters >= start_pore_diam) & (diameters <= end_pore_diam)])
    total_V_full = np.max(cum_V)
    total_A_full = np.max(cum_A)

    max_D_user = diameters[np.argmax(dV_dD[(diameters >= start_pore_diam) & (diameters <= end_pore_diam)])]
    max_D_full = diameters[np.argmax(dV_dD)]

    dV_D = diameters * diff_V
    ave_D_user = np.sum(dV_D[(diameters >= start_pore_diam) & (diameters <= end_pore_diam)]) / \
        np.sum(diff_V[(diameters >= start_pore_diam) & (diameters <= end_pore_diam)])
    ave_D_full = np.sum(dV_D) /np.sum(diff_V)
    
    # make all negative values to be zeros
    dV_dD[dV_dD < 0.] = 0.
    dA_dD[dA_dD < 0.] = 0.
    dV_dlogD[dV_dlogD < 0.] = 0.
    dA_dlogD[dA_dlogD < 0.] = 0.

    # print(total_A_full, total_A_user, total_V_full, total_V_user)
    # print(np.array([dV_dD, dV_dlogD]).T)

    # returning starting from 1 idex, because values at 0 index are zeros
    return {
        'D': diameters[1:],
        'dV': diff_V[1:],
        'V': cum_V[1:],
        'dV_dD': dV_dD[1:],
        'dV_dlogD': dV_dlogD[1:],
        'dA': diff_A[1:],
        'A': cum_A[1:],
        'dA_dD': dA_dD[1:],
        'dA_dlogD': dA_dlogD[1:],
        'total_V_user': total_V_user,
        'total_V_full': total_V_full,
        'total_A_user': total_A_user,
        'total_A_full': total_A_full,
        'max_D_user': max_D_user,
        'max_D_full': max_D_full,
        'ave_D_user': ave_D_user,
        'ave_D_full': ave_D_full,
    }


def write_graphs_to_worksheet(wsh, graphs, offset=0):
    for row in range(3):
        for col in range(len(graphs[row])):
            wsh.write(row, col + offset, graphs[row][col])
    for col in range(len(graphs[3])):
        for row in range(len(graphs[3][col])):
            wsh.write(row + 3, col + offset, graphs[3][col][row])


def calc_file(fname, write_summary=True, write_xls=True, start_pore_diam=2.5, end_pore_diam=90.,
    summary_vals=SUMMARY_VALS, graph_vals=GRAPH_VALS):
    """Parses one file and saves the specified values."""
    iso = parse_isotherms(fname)

    bet_data = calc_BET(iso['ads_p_q'])

    bjh_ads = calc_BJH(iso['ads_p_q'], start_pore_diam=start_pore_diam, end_pore_diam=end_pore_diam)
    bjh_des = calc_BJH(iso['des_p_q'], start_pore_diam=start_pore_diam, end_pore_diam=end_pore_diam)

    # additional titles o be places in xlsx file to discriminate between adsorption and desorption
    additional_titles = ['', '', 'Desorption ', 'Adsorption ']
    all_data = [bet_data, iso, bjh_des, bjh_ads]

    # rearrange data to summary and data for graphs
    summary = [list(), list(), list()]
    for idx, data in enumerate(all_data):
        for summary_val in summary_vals:
            if summary_val in data:
                summary[0].append(additional_titles[idx] + HEADER_TITLE[summary_val])
                summary[1].append(HEADER_UNITS[summary_val])
                summary[2].append(data[summary_val])
    # print(summary)
    
    graphs = [list(), list(), list(), list()]
    for idx, data in enumerate(all_data):
        for graph_val in graph_vals:
            if graph_val in data:
                graphs[0].append(additional_titles[idx] + HEADER_TITLE[graph_val])
                graphs[1].append(HEADER_UNITS[graph_val])
                graphs[2].append(get_sample_name(fname))
                graphs[3].append(data[graph_val])

    # print(bjh_des)
    # plt.semilogx(bjh_des['D'][bjh_des['D'] > 2.3], bjh_des['dV_dD'][bjh_des['D'] > 2.3], '*-')
    # plt.show()

    excel_fname = os.path.splitext(fname)[0] + '_calc.xlsx'
    # if there exists file with such name already - then delete it
    # because XlsxWriter 
    with xlsxwriter.Workbook(excel_fname) as wb:
        wsh = wb.add_worksheet('Calculated')

        # offset is needed when writing to worksheet
        offset = 0

        if write_summary:
            wsh.write('A1', 'Sample')
            wsh.write('A3', get_sample_name(fname))
            offset = offset + 1
            for row in range(len(summary)):
                for col in range(len(summary[row])):
                    wsh.write(row, col + offset, summary[row][col])
            offset = offset + len(summary[0]) + 1

        write_graphs_to_worksheet(wsh, graphs, offset=offset)

    # for old OriginPro that cannot import xlsx files.
    """
    if write_xls:
        # fisrt delete old xls file to avoid override prompts
        if os.path.exists(excel_fname + '.xls'):
            os.remove(excel_fname + '.xls')
        import xlwings as xw
        from xlwings.constants import FileFormat
        xw.App().visible = False
        wb = xw.Book(excel_fname)
        wb.api.SaveAs(excel_fname + '.xls', FileFormat.xlExcel8)
        wb.close()
    """

    return summary


if __name__ == '__main__':

    user_input = input('The calculation will override all the existing xlsx files. Do you want to continue (y/n)?\n')
    if user_input == 'y':

        # values to save
        summary_vals = [
            'bet_A', 
            'total_A_user',
            'total_V_full',
            'ave_D_user',
            ]

        # graph value list
        graph_vals = [
            'iso_p',
            'iso_q',
            'D',
            'dV_dD',
            'dV_dlogD',
            'V',
            'dA_dD',
            'dA_dlogD',
            'A',
        ]
        start_pore_diam=2.5
        end_pore_diam=90.

        # check if directory or file
        if len(sys.argv) >= 2:
            dir_or_file = sys.argv[1]
        else:
            dir_or_file = os.getcwd()

        if not os.path.isabs(dir_or_file):
            dir_or_file = os.path.join(os.getcwd(), dir_or_file)

        if os.path.isdir(dir_or_file):
            print(dir_or_file)
            dir = dir_or_file

            
            summaries = list()
            summary = None # needed to get the column titles

            for fname in glob.glob(os.path.join(dir, '*.txt')):
                print('\nCalculating ' + fname + '...')
                summary = calc_file(fname, write_summary=False, start_pore_diam=start_pore_diam,
                    end_pore_diam=end_pore_diam, summary_vals=summary_vals, graph_vals=graph_vals)
                summaries.append([get_sample_name(fname)] + summary[2])
                print('Done!')

            # in case of batch parsing, we save the summaries of each sample into
            # separate file
            print('\nSaving summaries...')

            with xlsxwriter.Workbook(os.path.join(dir, 'summary_calc.xlsx')) as wb:
                wsh = wb.add_worksheet('Summary')

                # write the first sample in the list and the column titles
                # wsh.write('A1', 'Sample')
                # wsh.write('A3', summaries[0][0][2])
                # add summary headers
                summaries = [['Sample'] + summary[0]] + [[''] + summary[1]] + summaries
                for row in range(len(summaries)):
                    for col in range(len(summaries[row])):
                        wsh.write(row, col, summaries[row][col])
            

        elif os.path.isfile(dir_or_file):
            fname = dir_or_file
            calc_file(fname, write_summary=False, start_pore_diam=start_pore_diam,
                end_pore_diam=end_pore_diam, summary_vals=summary_vals, graph_vals=graph_vals)

        else:
            print("Error: file or directory was not found.")

    else:
        print('Aborting')