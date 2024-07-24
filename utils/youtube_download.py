import argparse
import os

import pytube
import ffmpeg


# fixing the HTTP Error 400: Bad Request bug, probably it will be
# fixed in future releases of pytube
# https://github.com/pytube/pytube/issues/1973
from pytube import cipher
from http_400_bug import get_throttling_function_name
cipher.get_throttling_function_name = get_throttling_function_name


def download_video(video, dir=None, res='1080p', mime_type='video/mp4'):
    """Downloads video and audio with for the specified media quality and 
    then merges them into one file. Requires ffmpeg 
    https://anaconda.org/conda-forge/ffmpeg and ffmpeg-python."""
    
    if dir is None:
        dir = os.getcwd()
    
    if not os.path.exists(dir):
        os.mkdir(dir)
    
    if isinstance(video, str):
        yt = pytube.YouTube(video)
    else:
        yt = video
    yt.streams.filter(res=res, mime_type=mime_type).first().download(filename='video.mp4')
    yt.streams.filter(mime_type='audio/mp4').first().download(filename='audio.mp4')
    
    video = ffmpeg.input('video.mp4')
    audio = ffmpeg.input('audio.mp4')
    ffmpeg.concat(video, audio, v=1, a=1).output(os.path.join(dir, yt.title + '.mp4')).run()
    os.remove('video.mp4')
    os.remove('audio.mp4')
    
    
def download_playlist(playlist, dir=None, res='1080p', mime_type='video/mp4', start=1, end=100000):
    """Downloads playlist."""
    
    p = pytube.Playlist(playlist)
    try:
        title = p.title
    except KeyError:
        print('Not a playlist')
        return
    
    if dir is None:
        dir = os.path.join(os.getcwd(), title)
    
    if not os.path.exists(dir):
        os.mkdir(dir)
        
    for idx, video in enumerate(p.videos):
        if idx >= start - 1 and idx <= end - 1:
            print(f'Downloading video {idx} out of {min([len(p.videos), end])}.')
            download_video(video, dir=dir, res=res, mime_type=mime_type)


class YTDownloadParser(argparse.ArgumentParser):
    '''Class to perform parsing and checking of input arguments.'''
    
    def error(self, message):
        super().error(message)
        
    def parse_args(self) -> argparse.Namespace:
        args = super().parse_args()
        
        if args.playlist is None and args.video is None:
            self.error('Either video (-v) or playlist (-p) must be specified')
        
        if args.directory is None:
            args.directory = os.getcwd()
        
        return args

parser = YTDownloadParser(description='''Downloads youtube video or playlist.''')
parser.add_argument('-p', '--playlist', metavar='playlist', type=str,
                    help='''YouTube link to the playlist or url to video containing playlist id.''')
parser.add_argument('-v', '--video', metavar='video', type=str,
                    help='''YouTube link to the video.''')
parser.add_argument('-d', '--directory', metavar='directory', type=str, default=None,
                    help='''Directory to save video or playlist.''')
parser.add_argument('-r', '--resolution', metavar='resolution', type=str, default='1080p',
                    help='''Video resolution (e.g. 1080p).''')
parser.add_argument('-m', '--mime-type', metavar='mime_type', type=str, default='video/mp4',
                    help='''Video mime type (e.g. video/mp4).''')
parser.add_argument('-ps', '--playlist-start', type=int, default=1,
                    help='''Index of first video in playlist to dowload.''')
parser.add_argument('-pe', '--playlist-end', type=int, default=100000,
                    help='''Index of the last video in playlist to download.''')

if __name__ == '__main__':
    args = parser.parse_args()
    if args.playlist:
        download_playlist(args.playlist, dir=args.directory, res=args.resolution, 
                          mime_type=args.mime_type, start=args.playlist_start, 
                          end=args.playlist_end)
    if args.video:
        download_video(args.video, dir=args.directory, res=args.resolution, mime_type=args.mime_type)