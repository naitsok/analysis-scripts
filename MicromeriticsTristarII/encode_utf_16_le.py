# Encodes old Tristar files, which were in ANSI encoding to
# new Tristar files, which are in UTF-16-LE encoding

import sys, os, glob

if __name__ == '__main__':
    user_input = input('The parsing will override all the existing TXT file. Do you want to continue (y/n)?\n')
    if user_input == 'y':
        if len(sys.argv) >= 2:
            dir = sys.argv[1]
        else:
            dir = os.getcwd()
    
        for fname in glob.glob(os.path.join(dir, '*.txt')):
            with open(fname, 'r', encoding='ansi') as file:
                data = file.read()
            with open(fname, 'w', encoding='utf-16-le') as file:
                file.write(data)