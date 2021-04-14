# parses the Trisar Micrometric results files into Excel .xlsx file
# parses either a directory or a single file
# need XlsxWriter Python module (available in Anaconda by default)
# Python 3
# 

import xlsxwriter

import sys
import os
import glob
import re


def get_sample_name(fname):
    """Gets only the sample name from the full path provided by fname"""
    return os.path.splitext(os.path.basename(fname))[0]


def get_custom_table(fname, table_beginning):
    """Gets the values of the table specified by the table_beginning string"""

    with open(fname, encoding='utf-16-le') as file:

        # searching for table with values
        p = re.compile(table_beginning + '[\n\s]*(((\d+([.,]+[\de-]+)?)\s+(\d+([.,]+[\de-]+)?)\s*\n+)*)', re.IGNORECASE)
        # get only the part with numbers to exctract them afterwards
        values_only = p.search(file.read())

        # check if values were found
        if values_only is None:
            print(table_beginning + ' was not found. Check Tristar file and/or regular expression.')
            return [[0.], [0.]]

        # now get the values
        result_x = list()
        result_y = list()
        p = re.compile(r'(\d+(.\d+)?)\s+(\d+(.[\de-]+)?)')
        for iter in p.finditer(values_only.group(1)):
            result_x.append(float(iter.group(1).replace(',', '.')))
            result_y.append(float(iter.group(3).replace(',', '.')))

    return [result_x, result_y]


def get_summary_val(fname, vname):
    """Gets value of a summary variable from file 'fname' and 
    variable 'vname' in line of text
    Returns value and unit"""
    
    with open(fname, encoding='utf-16-le') as file:
        p = re.compile(vname + r'[ \w\.\,\n\(\)\/]*: +(\d+([.,]+[\de-]+)?)\,?\s+([\w\/]+)', re.IGNORECASE | re.UNICODE)
        m = p.search(file.read())

        # Check the desired summary value was found
        if m is None:
            print('No ' + vname + ' was found. Check the Tristar file and/or regular expression.')
            return [0, '']

    return [vname, m.group(3), float(m.group(1).replace(',', '.'))]


def write_to_worksheet(worksheet, data, col_offset):
    """Saves the data in format [[column 1], [column 2]] to the specified
    worksheet by the specified column offset"""

    for col in range(len(data)):
            for row in range(len(data[0])):
                worksheet.write(row, col + col_offset, data[col][row])


def parse_summary(fname):
    """Parses the summary, that is usually at the beginning of the tristar file
    Returns:
        [BET Surface Area, """

    print('Searching for summary values...')  
        
    search_vals = ['BET surface area',
                   'BJH Adsorption cumulative surface area of pores',
                   'BJH Desorption cumulative surface area of pores',
                   'BJH Adsorption cumulative volume of pores',
                   'BJH Desorption cumulative volume of pores',
                   'BJH Adsorption average pore',
                   'BJH Desorption average pore',
                   'Sample Mass',
                   # 'Standard Deviation of Fit',
                   ]

    summary = list()
    for val in search_vals:
        result = get_summary_val(fname, val)
        summary.append(result)

    return summary


def parse_isotherm(fname):
    """Get the adsorption-desorption isotherm"""

    print('Searching for adsorption-desorption isotherm data...')

    ads_branch = get_isoterm_branch(fname, 'Adsorption')
    des_branch = get_isoterm_branch(fname, 'Desorption')

    return [['Relative Pressure', r'p/p°', 'Adsorption-desorption isotherm'] + ads_branch[0] + des_branch[0], 
            ['Quantity Adsorbed', r'cm3/g', get_sample_name(fname)] + ads_branch[1] + des_branch[1]]


def get_isoterm_branch(fname, branch):
    """Gets values for either adsorption or desorption branch of the isotherm"""

    table_beginning = r'\-\s+' + branch + r'[\s\n]+Relative Pressure[a-zA-Z°³\/\(\)\n\sі]*'

    return get_custom_table(fname, table_beginning)


def parse_des_dV_dw_pore_volume(fname):
    """Get BJH Desorption dV/dw Pore Volume"""

    print('Searching for BJH Desorption dV/dw Pore Volume data...')

    table_beginning = r'BJH Desorption dV\/d[wD]+[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Volume \(cm[і³]?\/[g·nmÅЕ]*\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dV/dw Desorption Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'dV/dw', get_sample_name(fname)] + pore_vol[1]]


def parse_ads_dV_dw_pore_volume(fname):
    """Get BJH Adsorption dV/dw Pore Volume"""

    print('Searching for BJH Adsorption dV/dw Pore Volume data...')

    table_beginning = r'BJH Adsorption dV\/d[wD]+[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\sPore Volume \(cm[і³]?\/[g·nmÅЕ]*\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dV/dw Adsorption Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'dV/dw', get_sample_name(fname)] + pore_vol[1]]


def parse_des_dV_dlogw_pore_volume(fname):
    """Get BJH Desorption dV/dlog(w) Pore Volume"""

    print('Searching for BJH Desorption dV/dlog(w) Pore Volume data...')

    table_beginning = r'BJH Desorption dV\/dlog[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Volume \(cm[і³]?\/[g·nmÅЕ]*\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dV/dlog(w) Desorption Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'dV/dlog(w)', get_sample_name(fname)] + pore_vol[1]]


def parse_ads_dV_dlogw_pore_volume(fname):
    """Get BJH Adsorption dV/dlog(w) Pore Volume"""

    print('Searching for BJH Adsorption dV/dlog(w) Pore Volume data...')

    table_beginning = r'BJH Adsorption dV\/dlog[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Volume \(cm[і³]?\/[g·nmÅЕ]*\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dV/dlog(w) Adsorption Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'dV/dlog(w)', get_sample_name(fname)] + pore_vol[1]]


def parse_des_cum_pore_vol(fname):
    """Get BJH Desorption Cumulative Pore Volume."""

    print('Searching for BJH Desorption Cumulative Volume data...')

    table_beginning = r'BJH Desorption Cumulative[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\sPore Volume \(cm[і³]?\/g\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH Desorption Cumulative Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'cm3/g', get_sample_name(fname)] + pore_vol[1]]


def parse_ads_cum_pore_vol(fname):
    """Get BJH Adsorption Cumulative Pore Volume."""

    print('Searching for BJH Adsorption Cumulative Volume data...')

    table_beginning = r'BJH Adsorption Cumulative[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\sPore Volume \(cm[і³]?\/g\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH Adsorption Cumulative Pore Volume'] + pore_vol[0],
            ['Pore Volume', r'cm3/g', get_sample_name(fname)] + pore_vol[1]]


def parse_diff_pore_vol(fname):
    """Gets Differential Pore Volume vs. Pore Width"""

    print('Searching for Differential Pore Volume vs. Pore Width data...')

    table_beginning = r'Pore Width \(Nanometers\)\sDifferential Pore Volume \(cm[і³]?\/g\)'

    pore_vol = get_custom_table(fname, table_beginning)

    return [['Pore Width', 'nm', 'Differential Pore Volume vs. Pore Width'] + pore_vol[0],
            ['Pore Volume', r'cm3/g', get_sample_name(fname)] + pore_vol[1]]


def parse_des_dA_dw_pore_area(fname):
    """Get BJH Desorption dA/dw Pore Area"""

    print('Searching for BJH Desorption dA/dw Pore Area data...')

    table_beginning = r'BJH Desorption dA\/d[wD]+[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Area \(m[I²]?\/[g·nmÅЕ]*\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dA/dw Desorption Pore Area'] + pore_area[0],
            ['Pore Area', r'dA/dw', get_sample_name(fname)] + pore_area[1]]


def parse_ads_dA_dw_pore_area(fname):
    """Get BJH Adsorption dV/dw Pore Area"""

    print('Searching for BJH Adsorption dA/dw Pore Area data...')

    table_beginning = r'BJH Adsorption dA\/dw[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Area \(m[I²]?\/[g·nmÅЕ]*\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dV/dw Adsorption Pore Area'] + pore_area[0],
            ['Pore Area', r'dA/dw', get_sample_name(fname)] + pore_area[1]]


def parse_des_dA_dlogw_pore_area(fname):
    """Get BJH Desorption dA/dlog(w) Pore Area"""

    print('Searching for BJH Desorption dA/dlog(w) Pore Area data...')

    table_beginning = r'BJH Desorption dA\/dlog[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Area \(m[ІІ²]?\/[gnmÅ·Е]*\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dA/dlog(w) Desorption Pore Area'] + pore_area[0],
            ['Pore Area', r'dA/dlog(w)', get_sample_name(fname)] + pore_area[1]]


def parse_ads_dA_dlogw_pore_area(fname):
    """Get BJH Adsorption dA/dlog(w) Pore Area"""

    print('Searching for BJH Adsorption dA/dlog(w) Pore Area data...')

    table_beginning = r'BJH Adsorption dA\/dlog[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\s[0-9\-\w.\s\:\n\(\)\/]*\sPore Area \(m[IІ²]?\/[gnmÅ·Е]*\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH dA/dlog(w) Adsorption Pore Area'] + pore_area[0],
            ['Pore Area', r'dA/dlog(w)', get_sample_name(fname)] + pore_area[1]]


def parse_des_cum_pore_area(fname):
    """Get BJH Desorption Cumulative Pore Area."""

    print('Searching for BJH Desorption Cumulative Area data...')

    table_beginning = r'BJH Desorption Cumulative[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\sPore Area \(m[IІ²]?\/g\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH Desorption Cumulative Pore Area'] + pore_area[0],
            ['Pore Area', r'm2/g', get_sample_name(fname)] + pore_area[1]]


def parse_ads_cum_pore_area(fname):
    """Get BJH Adsorption Cumulative Pore Area."""

    print('Searching for BJH Adsorption Cumulative Area data...')

    table_beginning = r'BJH Adsorption Cumulative[0-9\-\w.\s\:\n\(\)\/]*Pore (Width|Diameter) \(nm\)\sPore Area \(m[IІ²]?\/g\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', r'nm', 'BJH Adsorption Cumulative Pore Area'] + pore_area[0],
            ['Pore Area', r'm2/g', get_sample_name(fname)] + pore_area[1]]


def parse_diff_pore_area(fname):
    """Gets Differential Surface Area vs. Pore Width"""

    print('Searching for Differential Surface Area vs. Pore Width data...')

    table_beginning = r'Pore Width \(Nanometers\)\sDifferential Surface Area \(m[І²]?/g\)'

    pore_area = get_custom_table(fname, table_beginning)

    return [['Pore Width', 'nm', 'Differential Pore Area vs. Pore Width'] + pore_area[0],
            ['Pore Area', r'm2/g', get_sample_name(fname)] + pore_area[1]]


def parse_goodness_of_fit(fname):
    """Gets the Goodness of Fit data: Input Data and Model Data"""

    print('Searching for Goodness of Fit data...')

    # First get Input Data
    table_beginning = r'Input Data[\s\n]*Relative Pressure \(p\/p°\)\sQuantity Adsorbed \(cm[і³]?\/g STP\)'
    input_data = get_custom_table(fname, table_beginning)
    input_data = [['Relative Pressure', r'p/p°', 'Goodness of Fit: Input Data'] + input_data[0],
                  ['Quantity Adsorbed', r'cm3/g', get_sample_name(fname)] + input_data[1]]

    # Now get Model Fit
    table_beginning = r'Model Fit[\s\n]*Relative Pressure \(p\/p°\)\sQuantity Adsorbed \(cm[і³]?\/g STP\)'
    model_fit = get_custom_table(fname,table_beginning)
    model_fit = [['Relative Pressure', r'p/p°', 'Goodness of Fit: Model Fit'] + model_fit[0],
                 ['Quantity Adsorbed', r'cm3/g', get_sample_name(fname)] + model_fit[1]]

    return [input_data, model_fit]



def parse_file(fname, write_parsed=True, write_summary=True):
    """Parses one file and saves the *.xlsx file with the same name.
    If write_summary is True writes the summary values to the excel file.
    If write_summary is False, then does not write. Needed when a batch of files is processed and 
    a separate summary file is generated for all the samples.
    """
    excel_fname = os.path.splitext(fname)[0] + '.xlsx'
    # if there exists file with such name already - then delete it
    # because XlsxWriter 
    summary = parse_summary(fname)

    if write_parsed:
        with xlsxwriter.Workbook(excel_fname) as wb:
            wsh = wb.add_worksheet('Parsed')

            # offset is need depending if the summary is written to file
            offset = 0
        
            if write_summary:
                wsh.write('A1', 'Sample')
                wsh.write('A3', get_sample_name(fname))            
                write_to_worksheet(wsh, summary, 1)
                offset = 10

            isotherm = parse_isotherm(fname)
            write_to_worksheet(wsh, isotherm, offset)

            # Desorption pore volume
            # bjh_des_pore_vol = parse_des_dV_dw_pore_volume(fname)
            bjh_des_pore_vol = parse_des_dV_dlogw_pore_volume(fname)
            write_to_worksheet(wsh, bjh_des_pore_vol, offset + 3)

            # Adsorption pore volume
            # bjh_ads_pore_vol = parse_ads_dV_dw_pore_volume(fname)
            bjh_ads_pore_vol = parse_ads_dV_dlogw_pore_volume(fname)
            write_to_worksheet(wsh, bjh_ads_pore_vol, offset + 6)

            # Desorption cumulative pore volume
            bjh_des_cum_pore_vol = parse_des_cum_pore_vol(fname)
            write_to_worksheet(wsh, bjh_des_cum_pore_vol, offset + 9)

            # Adsorption cumulative pore volume
            bjh_ads_cum_pore_vol = parse_ads_cum_pore_vol(fname)
            write_to_worksheet(wsh, bjh_ads_cum_pore_vol, offset + 12)

            # Desorption pore area
            bjh_des_pore_area = parse_des_dA_dlogw_pore_area(fname)
            write_to_worksheet(wsh, bjh_des_pore_area, offset + 15)

            # Adsorption pore area
            bjh_ads_pore_area = parse_ads_dA_dlogw_pore_area(fname)
            write_to_worksheet(wsh, bjh_ads_pore_area, offset + 18)

            # Desorption cumulative pore area
            bjh_des_cum_pore_area = parse_des_cum_pore_area(fname)
            write_to_worksheet(wsh, bjh_des_cum_pore_area, offset + 21)

            # Adsorption cumulative pore area
            bjh_ads_cum_pore_area = parse_ads_cum_pore_area(fname)
            write_to_worksheet(wsh, bjh_ads_cum_pore_area, offset + 24)

            # diff_pore_area = parse_diff_pore_area(fname)
            # write_to_worksheet(wsh, diff_pore_area, offset + 9)

            # diff_pore_vol = parse_diff_pore_vol(fname)
            # write_to_worksheet(wsh, diff_pore_vol, offset + 12)

            # goodness_of_fit = parse_goodness_of_fit(fname)
            # write_to_worksheet(wsh, goodness_of_fit[0], offset + 15)
            # write_to_worksheet(wsh, goodness_of_fit[1], offset + 17)

    return summary



if __name__ == '__main__':

    user_input = input('The parsing will override all the existing xlsx file. Do you want to continue (y/n)?\n')
    if user_input == 'y':

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

            for fname in glob.glob(os.path.join(dir, '*.txt')):
                print('\nParsing ' + fname + '...')
                summary = parse_file(fname, write_parsed=False, write_summary=False)
                summaries.append([['', '', get_sample_name(fname)]] + summary)
                print('Done!')

            # in case of batch parsing, we save the summaries of each sample into
            # separate file
            print('\nSaving summaries...')

            with xlsxwriter.Workbook(os.path.join(dir, 'summary.xlsx')) as wb:
                wsh = wb.add_worksheet('Summary')

                # write the first sample in the list and the column titles
                wsh.write('A1', 'Sample')
                wsh.write('A3', summaries[0][0][2])
                write_to_worksheet(wsh, summaries[0][1:], 1)

                # write the rest of the summary
                for row in range(1, len(summaries)):
                    for col in range(len(summaries[0])):
                        wsh.write(row + 2, col, summaries[row][col][2])

        elif os.path.isfile(dir_or_file):
            fname = dir_or_file
            parse_file(fname)

        else:
            print("Error: file or directory was not found.")

    else:
        print('Aborting')
