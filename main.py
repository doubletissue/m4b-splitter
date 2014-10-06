import argparse
import os
import re
import subprocess

def convert_files(directory, output_format):

    chapter_pattern = re.compile('^Chapter #(\d+)\.(\d+): start (\d+\.\d+), end (\d+\.\d+)$')

    for dirpath, dirname, filename in os.walk(directory):
        if filename and filename[0].endswith('.m4b'):
            filename = filename[0]
            try:
                info = subprocess.check_output(['ffprobe', os.path.join(dirpath, filename)], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as ex:
                print ex
                continue
            for line in info.split('\n'):
                line = line.strip()
                match = regex_pattern.match(line)
                if not match:
                    continue
                chapter_num = match.group(1)
                chapter_subnum = match.group(2)
                start_time = match.group(3)
                end_time = match.group(4)
                duration = str(float(end_time) - float(start_time))

                new_filename = filename.replace('.m4b','')
                new_filename = new_filename + '_' + chapter_num + '.' + chapter_subnum + '.' + output_format
                command = ['ffmpeg','-ss',start_time,'-t',duration,
                           '-i',os.path.join(dirpath,filename),os.path.join(dirpath,new_filename)]
                print ' '.join(command)
                subprocess.call(command)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert audiobook files')
    parser.add_argument('directory', help='directory to crawl for files')
    parser.add_argument('-o', '--output', dest='output', action='store', default='mp3', help='Output format')

    args = parser.parse_args()
    convert_files(args.directory,args.output)
