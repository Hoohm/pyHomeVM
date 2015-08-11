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
            if(re.match('local_root_dir', line)):
                global local_root_dir
                local_root_dir = line.split('=')[1].strip(' \'\n')
            elif(re.match('remote_root_dir', line)):
                global remote_root_dir
                remote_root_dir = line.split('=')[1].strip(' \'\n')
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


def createFolderID(folder_path):
    '''
    Function that takes a folder and returns a unique ID to
    identify a specific content of folder.
    Input: folder_path as string
    Output: ID as string'''
    folder_profile = ''
    folder_list = {}
    for filename in listVideoFiles(folder_path):  # loop files
        cur_path = os.path.join(folder_path, filename)
        folder_list[filename] = md5ForFile(cur_path)
    for filename in sorted(folder_list.keys()):
        folder_profile += folder_list[filename]
        folder_profile += str(os.path.getsize(cur_path))
    return(folder_profile)


def listVideoFiles(folder_path):
    '''Function that lists the video files found in a folder
    Input: folder_path as string
    Output: list of videos
    '''
    return [i
        for i in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, i))
        and
        checkIfVid(os.path.join(folder_path, i))]


def getFolderVideoDetails(folder_path):
    '''Function that returns a dict created by getVideoDetails
    for each file in a folder.
    Input: folder_path as string
    Output: Dict with video details for each video
    '''
    video_details = {}
    for filename in listVideoFiles(folder_path):  # loop files
        cur_path = os.path.join(folder_path, filename)
        video_details[filename] = getVideoDetails(cur_path)
    return(video_details)


def writeStructure(structure, file_path=script_root_dir + '/dir_tree.txt'):
    '''Function that writes a dir structure to dir_tree.txt file
    Input: structure as dict, file_path as string
    Output: None
    '''
    with open(file_path, 'w') as outfile:
        json.dump(structure, outfile)


def readStructureFromFile(file_path=script_root_dir + '/dir_tree.txt'):
    '''
    Function that reads a structure file from a json file
    Input: file_path as string dir_tree.txt
    Output: structure as dict
    '''
    with codecs.open(file_path, 'r', 'utf-8') as f:
        try:
            structure = json.load(f)
        except:
            return {}
    return structure


def createStructureEntry(ID, structure, folder_path, video_details):
    '''
    Function that creates an entry in the structure object
    Input: ID, structure, folder_path, video_details
    Output: NA, changes strucure in place'''
    structure[ID] = {}  # Empty dict containing folder info
    structure[ID]['path'] = folder_path  # Fill path
    structure[ID]['video_details'] = video_details


def readStructure(local_root_dir):
    '''
    Function that reads the structure of the dirs of the videos
    Input: Base dirs as lit
    Output: Dict of dir structure of videos

    '''
    base_level = os.listdir(local_root_dir)
    structure = {}  # Create empty structure
    #structure_with_date = {}
    for level1 in base_level:  # loop years. Level1 are years
        #Only take folders that are assimilated to years, ex: 1999
        if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir(os.path.join(local_root_dir, level1))):  # condition level1
            for level2 in os.listdir(os.path.join(local_root_dir, level1).decode('utf-8')):
                if os.path.isdir(os.path.join(local_root_dir, level1, level2)):  # If is dir
                    current_path = u'/'.join([local_root_dir, level1, level2])  # Use folder as reference
                    ID = createFolderID(current_path)  # ID of the folder
                    if(ID == ''):
                        continue
                    else:
                        createStructureEntry(ID, structure, current_path, {})
    return (structure)


def checkDetailsCompatibility(folder_info):
    '''
    Function that checks that every video in one folder have the same
    resolution or framerate.
    If not, converts to the lowest standard of the different possibilities.
    Input: folder_info as dict of video details
    Output: changes as Bool
    '''
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
    '''
    Function that converts new videos to the base encoding chosen
    Input: folder_path as string
    Ouptut: changes as Bool
    '''
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
            if(video_details[video][3] is not None):  # Found creation time
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
    '''
    Function that converts a video with new options
    Input: file_path as string, creation_time as string, details as dict
    '''
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
    '''
    Function that executes a command to shell.
    Allows to waitbetween each command
    Input: command as string
    Ouptut: None
    '''
    logger.debug('Executing: {}'.format(command))
    proc = subprocess.Popen(command, shell=True)
    proc.wait()


def isFromNas(stdout):
    '''
    Function that checks if a video has been created on the NAS.
    Input: stdout as string
    Ouptut: True or False
    '''
    try:
        return(stdout['format']['tags']['composer'] == nas_composer_name)
    except:
        return(False)


def hasCreationTime(stdout):
    '''
    Function that checks if a video has a creation time/date.
    Input: stdout as string
    Ouptut: True or False
    '''
    try:
        return(stdout['format']['tags']['creation_time'])
    except:
        return(False)


def getVideoDetails(file_path):
    '''
    Function that takes a file and returns duration plus offset duration
    Input: file_path as string
    Output: video_details as dict
    '''
    file_path = file_path.encode('utf-8')
    command = (
        "{} -v error -show_format"
        "-show_streams -print_format json"
        "-sexagesimal '{}'"
        ).format(ffprobeExecutablePath, file_path).replace('\n', '')
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
    '''
    Function that converts deltatime into string making sure
    that the formatting is right for mkvmerge
    Input: time_to_convert as timedelta object
    Output: time as string
    '''
    result = str(time_to_convert)
    if(re.match('[0-9]{1,2}:[0-9]{2}:[0-9]{2}.[0-9]', result)):
        return(result)
    else:
        return(result + '.000000')


def addTime(t1, t2):
    '''
    Function that adds times
    Input: t1 and t2 as strings
    Ouptut: added time as deltatime object
    '''
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


def md5ForFile(file_path, block_size=128):
    '''
    Function that takes a file and returns the first 10 characters of a hash of
    the first 10 block of bytes
    Input: File
    Output: Hash of 10 blocks of 128 bits of size as string
    '''
    with open(file_path, 'r') as f:
        n = 1
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            n += 1
            if (n == 10):
                break
            md5.update(data)
    return (md5.hexdigest()[0:9])


def updateStructure(past_structure, new_structure):
    '''
    Function that compares two structures looking
    for new,modified,deleted folders/files
    Input: past_structure as dict, new_structure as dict
    Output: None, changes strucure in place
    '''
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
    '''
    Function that processes a folder. Checks if videos are new
    or not compatible and encodes them accordingly.
    Input: structure as dict, ID as string
    '''
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
    '''
    Function that gets le list of existing paths in a structure
    Input: Structure as dict
    Output: paths as list of strings
    '''
    paths = []
    for ID in structure.keys():
        paths.append(structure[ID]['path'])
    return(paths)


def syncDirTree():
    '''
    Function that copies the folder structure to the remote media player.
    Suppresses the folder that are empty and missing from the NAS
    Input: None
    Output: None
    '''
    logger.info('Syncing remote folders structure')
    executeCommand(
        (
            "rsync --delete -av -f\"- /*/*/*/\" -f\"- */*/*\" "
            "{} {}").format(local_root_dir + '/', remote_root_dir + '/')
        )


def transferLongVersions():
    '''
    Function that looks for mkv movies and sends them to the remote media player
    Input: None
    Output: None
    '''
    base_level = os.listdir(local_root_dir)
    long_videos = []
    for level1 in base_level:  # loop years. Level1 are years
        #Only take folders that are assimilated to years, ex: 1999
        if (re.match(r'^[0-9]{4}$', level1) and os.path.isdir(os.path.join(local_root_dir, level1))):  # condition level1
            for level2 in os.listdir(os.path.join(local_root_dir, level1).decode('utf-8')):
                folder_path = os.path.join(local_root_dir, level1, level2)
                long_videos.append([os.path.join(folder_path, i)
                    for i in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, i))
                    and os.path.splitext(i)[1] == '.mkv'])
    long_videos = [item for sublist in long_videos for item in sublist]  # Flatten the nested list
    for video in long_videos:
        executeCommand("mv '{}' '{}'".format(video.encode('utf-8'), '/'.join(video.replace(local_root_dir, remote_root_dir).split('/')[:-1]).encode('utf-8')+'/'))
    logger.info("Long versions have been sent")


def createLongVideo(folder_info):
    '''
    Function that runs mkvmerge to create a long version of list of videos.
    Needs a chapter file (see createChaptersList)
    Input: folder_info as dict
    Ouptut: None
    '''
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


def moveLongVideo(old_path, new_path, todo_file_path=script_root_dir + '/todo.sh'):
    '''
    Function that adds bash commands to move files on the remote storage
    as strings into a file (default = /share/Scripts/todo.sh)
    Input: old_path as string, new_path as string, todo_file_path as string
    Ouptut: None
    '''
    old_file_path = "{}/{}.mkv".format(os.path.join(old_path.replace(local_root_dir, remote_root_dir)).encode('utf-8'), os.path.basename(old_path).encode('utf-8'))
    new_file_path = "{}/{}.mkv".format(os.path.join(new_path.replace(local_root_dir, remote_root_dir)).encode('utf-8'), os.path.basename(new_path).encode('utf-8'))
    new_folder_path = new_path.replace(local_root_dir, remote_root_dir)
    #logger.info(old_file_path)
    output_string = "mkdir '{}'\n".format(new_folder_path.encode('utf-8'))
    output_string += "mv '{}' '{}'\n".format(
        old_file_path,
        new_file_path)
    with open(todo_file_path, "a") as todo:
        todo.write(output_string)



def executeToDoFile(todo_file_path=script_root_dir + '/todo.sh'):
    '''
    Function that runs each lines of todo.sh sequentially and erases them after
    Input: todo_file_path as string
    Ouptut: None
    '''
    logger.info("Executing todo.sh")
    while 1:
        with open(todo_file_path, 'r') as f:
            first = f.readline()
            logger.info(first)
            if(first == ''):
                break
            sub = subprocess.Popen(first, shell=True)
            sub.wait()
            if(sub.wait() != 0):
                logger.info(sub.wait())
        out = subprocess.Popen("sed '1d' '{}' > '{}'/tmpfile; mv tmpfile '{}'".format(todo_file_path, script_root_dir, todo_file_path), shell=True)
        out.wait()
    logger.info("Todo file done")


def createChaptersList(folder_info):
    '''
    Function that creates a file containning the video list and the duration of
    the videos to pass to mkvmerge to create a long version with chapters
    Input: folder_info as dict
    Ouptut: None
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
        else:# All the others
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


def mount(remote_root_dir, ip_addr):
    '''
    Function that checks if remote media is mounted
    Input: remote_root_dir as string
    Output: Bool
    '''
    if (not os.path.exists(remote_root_dir)):
        logger.info("making dir " + remote_root_dir)
        os.makedirs(remote_root_dir)
    try:
        proc = subprocess.Popen("mount -t cifs //{}{} -o username={},password={} {}".format(
            ip_addr,
            remote_root_dir,
            remote_usr, remote_pass,
            remote_root_dir)
        )
        stdout, err = proc.communicate()
        if proc.wait() == 0:
            logger.info("Mounted!")
            return True
    except:
        logger.info("Not mounted")
        return False


def checkIfVid(file_path, video_extentions):
    '''
    Function that checks if a file a video with known extension
    Input: file_path as string, video_extensions as list of strings
    Ouptut: Bool
    '''
    for ext in video_extensions:
        if(file_path.endswith(ext) or file_path.endswith(ext.upper())):
            return True
    else:
        return False

def configure():
    '''
    Function that checks weather there is a config file written
    '''
    pass


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
    updateStructure(past_structure, readStructure(local_root_dir))
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