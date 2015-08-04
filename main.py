'''
Video-sync. A tool that allows you to manage your holidays library and create 
long version of your holidays to enjoy on your media center
'''

import os
import json
import re
import codecs
import hashlib
from datetime import datetime
from datetime import timedelta
import subprocess
import copy
import logging
from config import *
from notifications import *


def loadConfigFile():
    with open('config.py', 'r') as f:
        for line in f:
            if(re.match('video_root_dir', line)):
                global video_root_dir
                video_root_dir = line.split('=')[1].strip(' \'\n')
            elif(re.match('popcorn_root_dir', line)):
                global popcorn_root_dir
                popcorn_root_dir = line.split('=')[1].strip(' \'\n')
            elif(re.match('ffmpegExecutablePath', line)):
                global ffmpegExecutablePath
                ffmpegExecutablePath = line.split('=')[1].strip(' \'\n')
            elif(re.match('ffprobeExecutablePath', line)):
                global ffprobeExecutablePath
                ffprobeExecutablePath = line.split('=')[1].strip(' \'\n')
            elif(re.match('mkvmergeExecutablePath', line)):
                global mkvmergeExecutablePath
                mkvmergeExecutablePath = line.split('=')[1].strip(' \'\n')
            elif(re.match('vcodec', line)):
                global vcodec
                vcodec = line.split('=')[1].strip(' \'\n')
            elif(re.match('acodec', line)):
                global acodec
                acodec = line.split('=')[1].strip(' \'\n')
            elif(re.match('log_folder', line)):
                global logFolder
                logFolder = line.split('=')[1].strip(' \'\n')


#Function that takes a folder and returns a unique ID to
#identify a specific content of folder.
#Input: path to folder as string
#Output: ID as string
def createFolderID(folder_path):
    folder_profile = ''
    folder_list = {}
    for filename in listVideoFiles(folder_path):  # loop files
        cur_path = os.path.join(folder_path, filename)
        #video_details[filename] = getVideoDetails(cur_path)
        folder_list[filename] = md5ForFile(cur_path)
    for filename in sorted(folder_list.keys()):
        folder_profile += folder_list[filename]
        folder_profile += str(os.path.getsize(cur_path))
    return(folder_profile)


def listVideoFiles(folder_path):
    return [i
        for i in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, i))
        and
        checkIfVid(os.path.join(folder_path, i))]


def getFolderVideoDetails(folder_path):
    video_details = {}
    for filename in listVideoFiles(folder_path):  # loop files
        cur_path = os.path.join(folder_path, filename)
        video_details[filename] = getVideoDetails(cur_path)
    return(video_details)


#Function that writes a dir structure to dir_tree.txt file
#Input: structure
#Output: NA
def writeStructure(structure, file=script_root_dir + '/dir_tree.txt'):
    with open(file, 'w') as outfile:
        json.dump(structure, outfile)


#Function that reads a dir file from a json file
#Input: dir_tree.txt file
#Output: structure dict
def readStructureFromFile(infile=script_root_dir + '/dir_tree.txt'):
    with codecs.open(infile, 'r', 'utf-8') as f:
        try:
            structure = json.load(f)
        except:
            return {}
    return structure


def createStructureEntry(ID, structure, folder_path, video_details):
    '''Function that creates an entry in the structure object
    - Input: ID, structure, folder_path, video_details
    - Output: NA, changes strucure in place'''
    structure[ID] = {}  # Empty dict containing folder info
    structure[ID]['path'] = folder_path  # Fill path
    structure[ID]['video_details'] = video_details


#Function that reads the structure of the dirs of the videos
#Input: Base dirs as lit
#Output: Dict of dir structure of videos
def readStructure(video_root_dir):
    base_level = os.listdir(video_root_dir)
    structure = {}  # Create empty structure
    #structure_with_date = {}
    for level1 in base_level:  # loop years. Level1 are years
        #Only take folders that are assimilated to years, ex: 1999
        if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir(os.path.join(video_root_dir, level1))):  # condition level1
            for level2 in os.listdir(os.path.join(video_root_dir, level1).decode('utf-8')):
                '''loop level2. Level2 are folder with videos in them.
                The name of the folder is the name of the future concatenated video
                '''
                if os.path.isdir(os.path.join(video_root_dir, level1, level2)):  # If is dir
                    current_path = u'/'.join([video_root_dir, level1, level2])  # Use folder as reference
                    ID = createFolderID(current_path)  # ID of the folder
                    if(ID == ''):
                        continue
                    else:
                        createStructureEntry(ID, structure, current_path, {})
    return (structure)


# When we have multiple videos in one folder and some have not the same
# codec or resolution, we have to either convert everything to fit
# or make multiple videos.
#Input: folder_info as dict and type of handling as 'multiple' or 'convert' (futur)
# default is multiple
#Output: NA, creates chapters files in folders
def checkDetailsCompatibility(folder_info):
    changes = False
    resolutions = {}
    frame_rates = {}
    for video in sorted(folder_info['video_details'].keys()):
        resolutions[folder_info['video_details'][video][2]] = 0
        frame_rates[folder_info['video_details'][video][5]] = 0
    if(len(resolutions) > 1 or len(frame_rates) > 1):
        os.chdir(folder_info['path'])
        if(not os.path.exists('ori_details')):
            os.makedirs('ori_details')
        resolution = min(resolutions)
        frame_rate = min(frame_rates)
        for video in sorted(folder_info['video_details'].keys()):
            if(folder_info['video_details'][video][2] == resolution
                and folder_info['video_details'][video][5] == frame_rate):
                continue
                logger.info(video + " is compatible")
            else:
                executeCommand("mv '{}' '{}'".format(
                    video,
                    'ori_details/' + video)
                )
                convertVideoDetails(
                    video,
                    folder_info['video_details'][video][3],
                    details={'resolution': resolution, 'frame_rate': frame_rate}
                    )
                changes = True
    return(changes)


def baseFolderConvertion(folder_path):
    video_details = getFolderVideoDetails(folder_path)
    changes = False
    logger.info('Working on folder: {}'.format(folder_path.encode('utf-8')))
    os.chdir(folder_path)
    if(not os.path.exists('temp')):
        os.makedirs('temp')

    for video in sorted(video_details.keys()):
        if(checkIfVid(video) and video_details[video][4] == nas_composer_name):
            logger.info(video + ' Already from nas')
            continue
        else:
            logger.info(video + ' Not from nas')
            executeCommand("mv '{}' '{}'".format(video, 'temp/' + video))
            if(video_details[video][3] is not None):  # Then we have a creation time
                creation_time = video_details[video][3]
            else:
                creation_time = time.strftime('%Y-%m-%d %H:%M:%S')
            command = (
                "{} -loglevel panic -y -i '{}' "
                "-rc_eq 'blurCplx^(1-qComp)' "
                "-c:v {} -c:a {} -preset {} -crf {} -t {} "
                "-metadata composer={} -metadata creation_time='{}' "
                "-movflags +faststart -pix_fmt yuv420p "
                "-profile:v high -level 3.1 '{}'").format(
                ffmpegExecutablePath,
                'temp/' + video,
                vcodec,
                acodec,
                ffmpeg_preset,
                ffmpeg_crf_base,
                '00:00:05',
                nas_composer_name,
                creation_time,
                os.path.splitext(video)[0] + '.mp4')
            executeCommand(command)
            changes = True

    #shutil.rmtree('temp', ignore_errors=True)
    return(changes)


def mvRoot():
    os.chdir(script_root_dir)


def convertVideoDetails(file_path, creation_time, details):
    command = (
        "{} -loglevel panic -y -i '{}' "
        "-rc_eq 'blurCplx^(1-qComp)' "
        "-vf scale={}:-1 -r {} -c:v {} -c:a {} -preset {} -crf {} "
        "-metadata composer='temp' -metadata creation_time='{}' "
        "-movflags +faststart -pix_fmt yuv420p "
        "-profile:v high -level 3.1 '{}'"
        ).format(
        ffmpegExecutablePath,
        'ori_details/' + file_path,
        details['resolution'].split('x')[0],
        details['frame_rate'],
        vcodec,
        acodec,
        ffmpeg_preset,
        ffmpeg_crf,
        creation_time,
        file_path)
    executeCommand(command)


def executeCommand(command):
    logger.debug('Executing: {}'.format(command))
    proc = subprocess.Popen(command, shell=True)
    proc.wait()



def isFromNas(stdout):
    try:
        return(stdout['format']['tags']['composer'] == nas_composer_name)
    except:
        return(False)
    return('FAIL')


def hasCreationTime(stdout):
    try:
        return(stdout['format']['tags']['creation_time'])
    except:
        return(False)
    return('FAIL')


#Function that takes a file and returns duration plus offset duration
#Input: filepath
#Output:
def getVideoDetails(filepath):
    filepath = filepath.encode('utf-8')
    command = """{} -v error -show_format -show_streams -print_format json
    -sexagesimal '{}'""".format(ffprobeExecutablePath, filepath).replace('\n', '')
    
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )

    stdout, err = proc.communicate()
    stdout = json.loads(stdout)
    for stream_num, stream in enumerate(stdout['streams']):
        if(stdout['streams'][stream_num]['codec_type'] == 'video'):
            temp = stdout['streams'][stream_num]
            video_resolution = '{}x{}'.format(temp['width'], temp['height'])
            r_frame_rate = temp['r_frame_rate']
            vid_duration = temp['duration']
            vid_offset = temp['start_time']
            total_duration = addTime(vid_duration, vid_offset)
            if(isFromNas(stdout)):
                return(
                    datetimeToStr(total_duration),
                    datetimeToStr(vid_offset),
                    video_resolution,
                    temp['tags']['creation_time'],
                    nas_composer_name, r_frame_rate
                    )
            elif(hasCreationTime(stdout)):
                return(
                    None,
                    None,
                    video_resolution,
                    temp['tags']['creation_time'],
                    None,
                    None
                    )
            else:
                return(None, None, None, None, None, None)


def datetimeToStr(time_to_convert):
    '''Function that converts deltatime into string making sure
    that the formatting is right for mkvmerge
    -Input: timedelta object
    -Output: time as string'''
    result = str(time_to_convert)
    if(re.match('[0-9]{1,2}:[0-9]{2}:[0-9]{2}.[0-9]', result)):
        return(result)
    else:
        return(result + '.000000')


def addTime(t1, t2):
    '''Function that adds times
    - Input: time 1 and time 2 as strings
    - Ouptut: added time as deltatime object'''
    t1 = datetime.strptime(t1, '%H:%M:%S.%f')
    t2 = datetime.strptime(t2, '%H:%M:%S.%f')
    deltat1 = timedelta(
        hours=t1.hour,
        minutes=t1.minute,
        seconds=t1.second,
        microseconds=t1.microsecond
        )
    deltat2 = timedelta(
        hours=t2.hour,
        minutes=t2.minute,
        seconds=t2.second,
        microseconds=t2.microsecond
        )
    return(deltat1 + deltat2)


def md5ForFile(filepath, block_size=128):
    '''Function that takes a file and gives back a hash of
    the first 10 block of bytes
    -Input: File
    -Output: Hash of 10 blocks of 128 bits of size as string'''
    with open(filepath, 'r') as f:
        n = 1
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            n += 1
            if (n == 10):
                break
            md5.update(data)
    return (md5.hexdigest()[0:9])


def color(string, color):
    '''Function to change color of stdouptut for readability in shell
    -Input: string to color and the wished format
    -Output: colored string'''
    if color == 'red':
        return "\033[31m" + string + "\033[0m"
    elif color == 'green':
        return "\033[32m" + string + "\033[0m"
    elif color == 'bold':
        return "\033[1m" + string + "\033[0m"
    elif color == 'yellow':
        return "\033[33m" + string + "\033[0m"


def updateStructure(past_structure, new_structure):
    '''Function that compares two dir structures and give our the differences
    -Input: two structure, present and past
    -Output:NA changes strucure in place'''
    new_paths = getPathList(new_structure)
    present_structure = copy.deepcopy(past_structure)
    for ID in past_structure.keys():
        if ID == '':  # Empty folder
            continue
        if ID in new_structure.keys():  # Hash found in the new struct
            if (past_structure[ID]['path'] == new_structure[ID]['path']):  # Nothing changed
                continue
            else:  # Folder moved
                logger.info("[MOVED]    " + past_structure[ID]['path'].encode('utf-8') + "\n" + "-------->: " + new_structure[ID]['path'].encode('utf-8'))
                present_structure[ID]['path'] = new_structure[ID]['path']
                moveLongVideo(past_structure[ID]['path'], present_structure[ID]['path'])
        else:  # Hash missing in the new struct. A) deleted or B) ition moied or C)  folder
            if(past_structure[ID]['path'] in new_paths):  # Modified
                folder_path = past_structure[ID]['path']
                logger.info("[MODIFIED] " + folder_path.encode('utf-8'))
                createStructureEntry(ID, present_structure, folder_path, getFolderVideoDetails(folder_path))
                present_structure = processFolder(present_structure, ID)
            else:  # No hash and no path -> Deleted
                logger.info("[DELETED]  " + past_structure[ID]['path'].encode('utf-8'))
                del present_structure[ID]
        writeStructure(present_structure)
    present_paths = getPathList(present_structure)  # Get an image of the current structure state
    for new_ID in new_structure.keys():  # Seek out new folders
        if new_ID not in present_structure.keys() and new_structure[new_ID]['path'] not in present_paths:  # New videos
            logger.info("[NEW]      " + new_structure[new_ID]['path'].encode('utf-8'))
            folder_path = new_structure[new_ID]['path']
            createStructureEntry(new_ID, present_structure, folder_path, getFolderVideoDetails(folder_path))
            present_structure = processFolder(present_structure, new_ID)
        writeStructure(present_structure)
    logger.info('Structure updated')


def processFolder(structure, ID):
    details_changes = False
    folder_path = structure[ID]['path']
    if(baseFolderConvertion(folder_path)):
        del(structure[ID])
        ID = createFolderID(folder_path)
        createStructureEntry(
            ID,
            structure,
            folder_path,
            getFolderVideoDetails(folder_path)
            )
    logger.info('Checking compatibility')
    if(checkDetailsCompatibility(structure[ID])):
        details_changes = True
    createChaptersList(structure[ID])
    createLongVideo(structure[ID])
    if(details_changes):
        executeCommand("mv ori_details/* .;rm -r ori_details")
    return(structure)


def getPathList(structure):
    '''Function that gets le lists of existing paths in a structure
    -Input: Structure_info
    -Output: list of paths(string)'''
    paths = []
    for ID in structure.keys():
        paths.append(structure[ID]['path'])
    return(paths)


def syncDirTree():
    logger.info('Syncing remote folders structure')
    executeCommand(
        (
            "rsync --delete -av -f\"- /*/*/*/\" -f\"- */*/*\" "
            "{} {}").format(video_root_dir + '/', popcorn_root_dir + '/')
        )


def transferLongVersions():
    base_level = os.listdir(video_root_dir)
    long_videos = []
    for level1 in base_level:  # loop years. Level1 are years
        #Only take folders that are assimilated to years, ex: 1999
        if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir(os.path.join(video_root_dir, level1))):  # condition level1
            for level2 in os.listdir(os.path.join(video_root_dir, level1).decode('utf-8')):
                folder_path = os.path.join(video_root_dir, level1, level2)
                long_videos.append([os.path.join(folder_path, i)
                    for i in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, i))
                    and os.path.splitext(i)[1] == '.mkv'])
    long_videos = [item for sublist in long_videos for item in sublist]  # Flatten the nested list
    for video in long_videos:
        executeCommand("mv '{}' '{}'".format(video.encode('utf-8'), '/'.join(video.replace(video_root_dir, popcorn_root_dir).split('/')[:-1]).encode('utf-8')+'/'))
    logger.info("Long versions have been sent")


def createLongVideo(folder_info):
    '''Function that runs mkvmerge to create a long version of list of videos. Needs a chapter file (see createChaptersList)
    -Input: structure_info
    -Ouptut: NA'''
    os.chdir(folder_info['path'])
    if(len(folder_info['video_details']) == 1):  # Only one video
        file_in = folder_info['video_details'].keys()[0]
    else:
        file_in = ' + '.join(sorted(folder_info['video_details'].keys()))  # More than one
    command = "{} {} --quiet --chapters chapters.txt -o '{}'".format(
        mkvmergeExecutablePath,
        file_in,
        os.path.basename(folder_info['path']).encode('utf-8') + '.mkv')
    executeCommand(command)


def moveLongVideo(old_path, new_path, todo_file=script_root_dir + '/todo.sh'):
    '''
    Function that adds bash commands as strings
    into a file (default = /share/Scripts/todo.sh)
    '''
    old_file_path = "{}/{}.mkv".format(os.path.join(old_path.replace(video_root_dir, popcorn_root_dir)).encode('utf-8'), os.path.basename(old_path).encode('utf-8'))
    new_file_path = "{}/{}.mkv".format(os.path.join(new_path.replace(video_root_dir, popcorn_root_dir)).encode('utf-8'), os.path.basename(new_path).encode('utf-8'))
    new_folder_path = new_path.replace(video_root_dir, popcorn_root_dir)
    #logger.info(old_file_path)
    output_string = "mkdir '{}'\n".format(new_folder_path.encode('utf-8'))
    output_string += "mv '{}' '{}'\n".format(
        old_file_path,
        new_file_path)
    with open(todo_file, "a") as todo:
        todo.write(output_string)



def executeToDoFile(file_to_exec=script_root_dir + '/todo.sh'):
    '''
    Function that runs each lines of todo.sh
    '''
    logger.info("Executing todo.sh")
    while 1:
        with open(file_to_exec, 'r') as f:
            first = f.readline()
            logger.info(first)
            if(first == ''):
                break
            sub = subprocess.Popen(first, shell=True)
            sub.wait()
            if(sub.wait() != 0):
                logger.info(sub.wait())
        out = subprocess.Popen("sed '1d' '{}' > '{}'/tmpfile; mv tmpfile '{}'".format(file_to_exec, script_root_dir, file_to_exec), shell=True)
        out.wait()
    logger.info("Todo file done")


def createChaptersList(folder_info):
    '''
    Function that creates a file containning the file list and the duration of the videos to create a new video
    Takes a folder in entry, creates a file
    '''
    time_format = re.compile('([0-9]{1,2}:[0-9]{2}:[0-9]{2}.[0-9]{3})')
    video_details = folder_info['video_details']
    output_string = ''
    for n, filename in enumerate(sorted(video_details)):
        if (n == 0):  # First Video
            output_string += 'CHAPTER{}={}\nCHAPTER{}NAME={}\n'.format(
                n,
                re.search(time_format, video_details[filename][1]).group(1),
                n,
                os.path.splitext(filename)[0].encode('utf-8')
                )
            last = addTime(
                video_details[filename][0],
                video_details[filename][1]
                )
        else:
            o = datetime.strptime(video_details[filename][1], '%H:%M:%S.%f')
            deltaO = timedelta(
                hours=o.hour,
                minutes=o.minute,
                seconds=o.second,
                microseconds=o.microsecond
                )
            output_string += 'CHAPTER{}={}\nCHAPTER{}NAME={}\n'.format(
                n,
                re.search(time_format, datetimeToStr(deltaO + last)).group(1),
                n,
                os.path.splitext(filename)[0].encode('utf-8'))
            last = addTime(video_details[filename][0], datetimeToStr(last))
    with open(folder_info['path'] + '/chapters.txt', 'w') as file_list:
        file_list.write(output_string.encode('utf-8'))


#Function that gets a key in a dict using its value
#Dict and key
def getKeyFromPath(structure, path):
    return structure.keys()[structure.values()['path'].index(value)]


def mount():
    '''Function that checks if remote media is mounted
    -Input:NA
    -Output: Bool'''
    if (not os.path.exists('/mnt/A410')):
        logger.info("making dir /mnt/A410")
        os.makedirs("/mnt/A410")
    try:
        proc = subprocess.Popen("mount -t cifs //192.168.1.41/share/Video -o username=nmt,password=12345 /mnt/A410/")
        stdout, err = proc.communicate()
        if proc.wait() == 0:
            logger.info("Mounted!")
            return True
    except:
        logger.info("Not mounted")
        return False


#Function that takes a file and tells if its a video or not
#Input: File
#Output: File or nothing
def checkIfVid(f):
    extension_list = ['.mp4', '.mpg', '.mpeg', '.avi', '.tod', '.vob', '.wmv']
    for ext in extension_list:
        if(f.endswith(ext) or f.endswith(ext.upper())):
            return True
    else:
        return False




#Main
############################################################################

today = datetime.now().strftime("%Y%m%d")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('log_' + today)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":
    #sys.stdout = Logger("log_{}.txt".format(today))
    try:
        open('dir_tree.txt', 'r')
        past_structure = readStructureFromFile('dir_tree.txt')
    except:
        logger.info("dir_tree.txt not found")
        past_structure = {}
    updateStructure(past_structure, readStructure(video_root_dir))
    if(mount()):
    #if(True):
        executeToDoFile()
        syncDirTree()
        transferLongVersions()
    else:
        pass
        #sendSmsNotification('The NAS is trying to reach the media center')
    #sendMailNotification(sys.tdout.encode('utf-8'))


# future module: http://code.activestate.com/recipes/577376-simple-way-to-execute-multiple-process-in-parallel/