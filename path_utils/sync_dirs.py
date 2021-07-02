# sync directories and files in the specified directories

import argparse
import os
import shutil


def sync_dirs(source_dir, target_dir):
    '''Performs the syncronization of directories.'''
    paths = os.listdir(source_dir)
    for path in paths:
        source_path = os.path.join(source_dir, path)
        target_path = os.path.join(target_dir, path)
        
        # compare source and target paths, delete target path if it does not exist 
        # in source paths
        if os.path.exists(target_path) and (not os.path.exists(source_path)):
            print(f'Not found {target_path} in {source_path}.\nRemoving {target_path}.')
            if os.path.isfile(target_path):
                os.remove(target_path)
            else:
                shutil.rmtree(target_path)
        
        # copy files or subdirectories


class SyncDirsParser(argparse.ArgumentParser):
    '''Class to perform parsing and checking of input arguments.'''
    
    def error(self, message):
        super().error(message)
        
    def parse_args(self) -> argparse.Namespace:
        args = super().parse_args()
        desc = ['source', 'target']
        
        # Check the supplied arguments
        for i, dir in enumerate([args.source_dir, args.target_dir]):
            if not os.path.exists(dir):
                self.error(f'Specified {desc[i]} directory does not exist: {dir}')
            if os.path.isfile(dir):
                self.error(f'Specified {desc[i]} directory is file and not directory: {dir}')
        
        return args
    
parser = SyncDirsParser(description='''Syncronizes two directories. After syncronization, 
                        the source and target directories contain the same subdirectories and files.''')
parser.add_argument('source_dir', metavar='source_dir', type=str,
                    help='''Source directory to syncronize from.''')
parser.add_argument('target_dir', metavar='target_dir', type=str,
                    help='''Target directory to syncronize to.''')