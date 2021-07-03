# sync directories and files in the specified directories

import argparse
import os
import shutil


def sync_dirs(source_dir, target_dir):
    '''Performs the syncronization of directories.'''
    source_paths = os.listdir(source_dir)
    
    # first check if there is something to delete in the target path
    for path in os.listdir(target_dir):
        if not path in source_paths:
            target_path = os.path.join(target_dir, path)
            print(f'Removing {target_path}. Not found in {source_dir}.')
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
    
    # now check and update depending what is new
    for path in source_paths:
        source_path = os.path.join(source_dir, path)
        target_path = os.path.join(target_dir, path)
        
        if os.path.isdir(source_path):
            # source path is directory, recursively apply sync_dirs() to it
            print(f'Entering directory {source_path}.')
            if not os.path.exists(target_path):
                os.mkdir(target_path)
                print(f'Created path {target_path}.')
            sync_dirs(source_path, target_path)
        else:
            # source path is file, update it if it is newer
            if not os.path.exists(target_path):
                # just copy new file
                try:
                    shutil.copy2(source_path, target_path)
                    print(f'File copied from {source_path} to {target_path}.')
                except:
                    print(f'FAILED COPY from {source_path} to {target_path}.')
            else:
                # update target file if necessary
                source_time = os.path.getmtime(source_path)
                target_time = os.path.getmtime(target_path)
                if source_time > target_time:
                    try:
                        shutil.copy2(source_path, target_path)
                        print(f'File updated from {source_path} to {target_path}.')
                    except:
                        print(f'FAILED UPDATE from {source_path} to {target_path}.')


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


if __name__ == '__main__':
    args = parser.parse_args()
    sync_dirs(args.source_dir, args.target_dir)