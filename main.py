import argparse
import os
import re
import subprocess
import threading

from collections import deque

# Simple threadpool to handle multithreaded conversion.
# It expects a "work unit" to be a list of arguments to
# be passed into a subprocess call. Add all your work, 
# then call "join" to wait for it to finish.
class Threadpool:
    def __init__(self, num_threads):
        self.work = deque()
        self.lock = threading.RLock()
        self.done = False
        self.threads = []
        for i in range(num_threads):
            t = threading.Thread(target=self._do_work)
            t.daemon = True
            t.start()
            self.threads.append(t)
    
    def add_work(self, work_unit, replace):
        self.lock.acquire()
        self.work.append( (work_unit, replace) )
        self.lock.release()

    def join(self):
        self.lock.acquire()
        self.done = True
        self.lock.release()
        for thread in self.threads:
            thread.join()

    def _do_work(self):
        while True:
            self.lock.acquire()
            if self.done and not self.work:
                self.lock.release()
                break
            elif not self.work:
                self.lock.release()
                continue
            work_unit, replace = self.work.popleft()
            print len(self.work),"left"
            print ' '.join(work_unit)
            self.lock.release()
            proc = subprocess.Popen(work_unit,stdin=subprocess.PIPE)
            if replace == 'yes':
                proc.communicate('y')
            elif replace == 'no':
                proc.communicate('n')
            else:
                c = raw_input().lower()
                while c != 'y' and c != 'n':
                    c = raw_input().lower()
                proc.communicate(c)

# Function that does all the work. Walks over the directory recursively and splits all
# m4b audiobook files it finds using the chapter metadata into files specified by the 
# output_format. It will use a threadpool with num_threads threads.
def convert_files(directory, output_format, num_threads, replace):

    threadpool = Threadpool(num_threads)
    
    # The pattern to find chapter info
    chapter_pattern = re.compile('^Chapter #(\d+)\.(\d+): start (\d+\.\d+), end (\d+\.\d+)$')
    # The pattern that finds the title for a chapter
    title_pattern = re.compile('^\s*title\s*:\s*(.*)$')
    # The pattern that tries to find a leading number on a title, to use as a track number
    track_pattern = re.compile('^(\d+).*$')
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith('.m4b'):
                try:
                    # ffprobe is normally packaged with ffmpeg. If you for some reason do not
                    # have ffprobe, a call to ffmpeg *should* do the same thing (it will produce 
                    # an error due to having no output but it will still give you the chapter data)
                    info = subprocess.check_output(['ffprobe', os.path.join(dirpath, filename)], stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as ex:
                    print ex
                    continue
                lines = info.split('\n')
                linenum = 0
                while linenum < len(lines):
                    line = lines[linenum]
                    line = line.strip()
                    chapter_match = chapter_pattern.match(line)
                    # If we found a chapter, skip ahead to the title and ignore the lines between them
                    if not chapter_match:
                        linenum += 1
                        continue
                    else:
                        title_match = title_pattern.match(lines[linenum+2])
                        linenum += 3
                    chapter_num = chapter_match.group(1)
                    chapter_subnum = chapter_match.group(2)
                    start_time = chapter_match.group(3)
                    end_time = chapter_match.group(4)
                    duration = str(float(end_time) - float(start_time))
                    
                    if title_match:
                        title = title_match.group(1)
                        track_match = track_pattern.match(title)
                        if track_match:
                            track = track_match.group(1)
                        else:
                            track = chapter_subnum
                    else:
                        print chapter_match.groups()
                        # Simple but lengthy new filename if there is no title
                        title = filename.replace('.m4b','') + '_' + chapter_num + '.' + chapter_subnum
                    new_filename = title + '.' + output_format
                    # subprocess.call(['rm',os.path.join(dirpath,new_filename)])
                    command = ['ffmpeg',
                               '-ss',start_time,
                               '-t',duration,
                               '-metadata','title='+title,
                               '-metadata','track='+track,
                               '-i',os.path.join(dirpath,filename),os.path.join(dirpath,new_filename)]
                    threadpool.add_work(command, replace)
    threadpool.join()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert audiobook files')
    parser.add_argument('directory', help='directory to crawl for files')
    parser.add_argument('-o', '--output', dest='output', action='store', 
                        default='mp3', help='Output format')
    parser.add_argument('-n', '--num-threads', dest='num_threads', type=int, 
                        action='store', default=1, help='Number of threads to convert with')
    parser.add_argument('-r', '--replace', dest='replace', action='store', 
                        default='no', choices=['yes','no','ask'], 
                        help='replace already existing files; "ask" will result in being prompted for each. "ask" will have unknown consequences with multithreading')
    
    args = parser.parse_args()
    convert_files(args.directory, args.output, args.num_threads, args.replace)
    # convert_files('/home/dan/Downloads/The Teaching Company~Burnedheal~')
