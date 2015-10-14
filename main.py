# coding=utf-8
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
import ConfigParser
import argparse
import traceback
import time
from notifications import sendMailReport, sendMailLog, sendSmsNotification
from string import Template


class Video(object):
    def __init__(self, file_path):
        self.path = file_path
        self.duration = None
        self.offset = None
        self.video_codec = None
        self.audio_codec = None
        self.author = None
        self.source = None
        self.resolution = None
        self.creation_time = None
        self.integrity = None

    def check_video_integrety(self):
        '''
        Verifies that the video can be encoded without any problem.
        Also checks if the duration of the video is correct
        '''
        cmd = "{} -v error -i '{}' null - 2".format(ffmpegExecutablePath, self.file_path)
        executeCommand(cmd)



def createFolderID(folder_path):
    '''
    Function that takes a folder path and returns a unique ID to
    identify a specific content of folder.
    Input: folder_path as string
    Output: ID as string
    '''
    folder_id = ''
    folder_list = {}
    for filename in listVideoFiles(folder_path):  # loop files
        cur_path = os.path.join(folder_path, filename)
        folder_list[filename] = md5ForFile(cur_path)
    for filename in sorted(folder_list.keys()):
        folder_id += folder_list[filename]
        folder_id += str(os.path.getsize(cur_path))
    return(folder_id)


def listVideoFiles(folder_path):
    '''
    Function that lists the video files found in a folder
    Input: folder_path as string
    Output: list of videos paths (as strings)
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
        temp_holder = getVideoDetails(cur_path)
        if(temp_holder):
            video_details[filename] = temp_holder
        else:
            continue
    return(video_details)


def writeStructure(structure, file_path):
    '''Function that writes a dir structure to dir_tree.json file
    Input: structure as dict, file_path as string
    Output: None
    '''
    with open(file_path, 'w') as outfile:
        json.dump(structure, outfile)


def readStructureFromFile(file_path):
    '''
    Function that reads a structure file from a json file
    Input: file_path as string dir_tree.json
    Output: structure as dict
    '''
    with codecs.open(file_path, 'r', 'utf-8') as f:
        try:
            structure = json.load(f)
        except Exception:
            logger.info(traceback.format_exc())
            return {}
    return structure


def createStructureEntry(ID, structure, folder_path, video_details, valid=False):
    '''
    Function that creates an entry in the structure object
    Input: ID, structure, folder_path, video_details
    Output: NA, changes strucure in place'''
    structure[ID] = {}
    structure[ID]['path'] = folder_path
    structure[ID]['video_details'] = video_details


def readStructure(local_root_dir):
    '''
    Function that reads the structure of the dirs of the videos
    Input: Base dirs as lit
    Output: Dict of dir structure of videos

    '''
    base_level = os.listdir(local_root_dir)
    structure = {}  # Create empty structure
    #try with os.walk
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


def baseFolderConvertion(folder_dict):
    '''
    Function that converts new videos to the base encoding options chosen
    Input: folder_path as string
    Ouptut: changes as Bool
    '''
    video_details = folder_dict['video_details']
    folder_path = folder_dict['path']
    changes = False
    logger.info('Working on folder: {}'.format(folder_path.encode('utf-8')))
    os.chdir(folder_path)
    if(not os.path.exists('temp')):
        os.makedirs('temp')
    for video in sorted(video_details.keys()):
        if(checkIfVid(video) and video_details[video][4] == nas_composer_name):
            logger.info('{} Already from nas'.format(video))
            continue
        else:
            logger.info('{} Not from nas'.format(video))
            executeCommand("mv '{}' '{}'".format(video, 'temp/' + video))
            if(video_details[video][3] is not None):  # Found creation time
                creation_time = video_details[video][3]
            else:
                creation_time = time.strftime('%Y-%m-%d %H:%M:%S')
            command = (
                "'{}' -loglevel panic -y -i '{}' "
                "-rc_eq 'blurCplx^(1-qComp)' "
                "-c:v {} -c:a {} -preset {} -crf {} "
                "-metadata composer={} -metadata creation_time='{}' "
                "-movflags +faststart -pix_fmt yuv420p "
                "-profile:v high -level 3.1 '{}'").format(
                ffmpegExecutablePath,
                'temp/' + video,
                vcodec,
                acodec,
                ffmpeg_preset,
                ffmpeg_crf_base,
                nas_composer_name,
                creation_time,
                os.path.splitext(video)[0] + '.mp4')
            executeCommand(command)
            changes = True

    #shutil.rmtree('temp', ignore_errors=True)
    return(changes)


def convertVideoDetails(file_path, creation_time, details):
    '''
    Function that converts a video with new options
    Input: file_path as string, creation_time as string, details as dict
    '''
    command = (
        "'{}' -loglevel panic -y -i '{}' "
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
        ffmpeg_crf_base,
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
    Input: stdout as dict
    Ouptut: True or False
    '''
    try:
        return(stdout['format']['tags'].get('composer') == nas_composer_name)
    except Exception:
        logger.info(traceback.format_exc())
        return(False)


def hasCreationTime(stdout):
    '''
    Function that checks if a video has a creation time/date.
    Input: stdout as string
    Ouptut: True or False
    '''
    try:
        return(stdout['format']['tags'].get('creation_time'))
    except Exception:
        logger.info(traceback.format_exc())
        return(False)


def getVideoDetails(file_path):
    '''
    Function that takes a file and returns duration plus offset duration
    Input: file_path as string
    Output: video_details as dict
    '''
    file_path = file_path.encode('utf-8')
    command = (
        "'{}' -v quiet -show_format "
        "-show_streams -print_format json "
        "-sexagesimal '{}'"
        ).format(ffprobeExecutablePath, file_path)
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
    stdout, err = proc.communicate()
    stdout = json.loads(stdout)
    streams = stdout.get('streams')
    if not streams:
        corrupted = os.path.join(os.path.dirname(file_path), 'corrupted')
        if(not os.path.exists(corrupted)):
            os.makedirs(corrupted)
            os.rename(file_path, os.path.join(corrupted, os.path.basename(file_path)))
            logger.info('{} is corrupted'.format(file_path))
            return(False)
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


def format_html(old_path, present_path, action, **file_paths):
    '''
    Function that takes two paths, and action and file lists
    and returns an html string that will be inserted in html_report
    Input: old_path as string, present_path as string, action as string
    file_paths as dict of files as string
    '''
    if(action == 'moved'):
        html_string = 'Le dossier <b>{}</b> en {} a été déplacé en {} sous <b>{}</b><br>'.format(
            old_path.split('/')[5],
            old_path.split('/')[4],
            present_path.split('/')[4],
            present_path.split('/')[5])
    if(action == 'modified'):
        html_string = 'Ce dossier a été modifié: <b>{}</b> en {}<br>'.format(
            present_path.encode('utf-8').split('/')[5],
            present_path.encode('utf-8').split('/')[4])
        new_files = file_paths['new_files']
        if(len(new_files) != 0):
            new_files_string = ''.join(['- {}<br>'.format(i) for i in new_files])
            html_string += 'le(s) fichier(s) suivant(s) ont été ajouté<br>{}<br>'.format(
                new_files_string.replace('\'', ''))
        del_files = file_paths['del_files']
        if(len(del_files) != 0):
            del_files_string = ''.join(['- {}<br>'.format(i) for i in del_files])
            html_string += 'Le(s) fichier(s) suivant(s) ont été effacé<br>{}<br>'.format(
                del_files_string.replace('\'', ''))
    if(action == 'deleted'):
        html_string = 'Le dossier <b>{}</b> en {} a été effacé<br><br>'.format(
            present_path.split('/')[5],
            present_path.split('/')[4])
    if(action == 'new'):
        html_string = 'Le dossier <b>{}</b> en {} est nouveau<br><br>'.format(
            present_path.encode('utf-8').split('/')[5],
            present_path.encode('utf-8').split('/')[4])
    return(html_string)


def updateStructure(past_structure, new_structure):
    '''
    Function that compares two structures looking
    for new,modified,deleted folders/files
    Input: past_structure as dict, new_structure as dict
    Output: None, changes strucure in place
    '''
    html_report = {'new': '', 'modified': '', 'moved': '', 'deleted': ''}
    new_paths = getPathList(new_structure)
    present_structure = copy.deepcopy(past_structure)
    for ID in past_structure.keys():
        if ID == '':  # Empty folder
            continue
        if ID in new_structure.keys():  # Hash found in the new struct
            if (past_structure[ID]['path'] == new_structure[ID]['path']):
                continue
            else:  # Folder moved
                old_path = past_structure[ID]['path'].encode('utf-8')
                new_path = new_structure[ID]['path'].encode('utf-8')
                logger.info('{} [MOVED] to ------> {}'.format(
                    old_path,
                    new_path))
                html_report['moved'] += format_html(old_path, new_path, action='moved')
                present_structure[ID]['path'] = new_structure[ID]['path']
                moveLongVideo(past_structure[ID]['path'], present_structure[ID]['path'])
        else:  # Hash missing in the new struct. Deleted or modified
            if(past_structure[ID]['path'] in new_paths):  # Modified
                folder_path = past_structure[ID]['path']
                logger.info('[MODIFIED] {}'.format(folder_path.encode('utf-8')))
                new_files = [
                    new for new in listVideoFiles(folder_path)
                    if new not in past_structure[ID]['video_details'].keys()]
                del_files = [
                    deleted for deleted in past_structure[ID]['video_details'].keys()
                    if deleted not in listVideoFiles(folder_path)]
                html_report['modified'] += format_html('', folder_path, action='modified', new_files=new_files, del_files=del_files)
                new_ID = createFolderID(folder_path)
                createStructureEntry(new_ID, present_structure, folder_path, getFolderVideoDetails(folder_path))
                present_structure = processFolder(present_structure, new_ID)
                del present_structure[ID]  # Delete old ID in structure
            else:  # No hash and no path -> Deleted
                folder_path = past_structure[ID]['path'].encode('utf-8')
                logger.info("[DELETED]  {}".format(folder_path))
                html_report['deleted'] += format_html('', folder_path, action='deleted')
                del present_structure[ID]
        writeStructure(present_structure, dir_tree_file)
    present_paths = getPathList(present_structure)  # Get list pf paths
    for new_ID in new_structure.keys():  # Seek out new folders
        if(new_ID not in present_structure.keys() and new_structure[new_ID]['path'] not in present_paths):  # New Videos
            folder_path = new_structure[new_ID]['path']
            logger.info("[NEW]   {}".format(folder_path.encode('utf-8')))
            html_report['new'] += format_html('', folder_path, action='new')
            createStructureEntry(new_ID, present_structure, folder_path, getFolderVideoDetails(folder_path))
            present_structure = processFolder(present_structure, new_ID)
        writeStructure(present_structure, dir_tree_file)
    logger.info('Structure updated')
    return(html_report)


def processFolder(structure, ID):
    '''
    Function that processes a folder. Checks if videos are new
    or not compatible and encodes them accordingly.
    Input: structure as dict, ID as string
    '''
    details_changes = False
    folder_path = structure[ID]['path']
    if(baseFolderConvertion(structure[ID])):
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


#Not implemented yet
def checkVideoIntegrity(file_path):
    '''
    Function that verifies if the video is corrupted or not and
    can be used for concatenation.
    '''
    pass
    video_details = getVideoDetails(file_path)
    if (video_details.get('duration')):
        pass


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
    logger.info("Long versions have been moved to remote")


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
    command = "{} {} --quiet --chapters {} -o '{}'".format(
        mkvmergeExecutablePath,
        file_in,
        chapters_file,
        os.path.basename(folder_info['path']).encode('utf-8') + '.mkv')
    executeCommand(command)
    os.remove(chapters_file)


def moveLongVideo(old_path, new_path):
    '''
    Function that adds bash commands to move files on the remote storage
    as strings into a file (default = /share/Scripts/todo.sh)
    Input: old_path as string, new_path as string, todo_file_path as string
    Ouptut: None
    '''
    output_string = ''
    old_file_path = "{}/{}.mkv".format(
        os.path.join(old_path.replace(local_root_dir, remote_root_dir)).encode('utf-8'),
        os.path.basename(old_path).encode('utf-8'))
    new_file_path = "{}/{}.mkv".format(
        os.path.join(new_path.replace(local_root_dir, remote_root_dir)).encode('utf-8'),
        os.path.basename(new_path).encode('utf-8'))
    new_folder_path = new_path.replace(local_root_dir, remote_root_dir)
    #logger.info(old_file_path)
    output_string += "mkdir '{}'\n".format(new_folder_path.encode('utf-8'))
    output_string += "mv '{}' '{}'\n".format(
        old_file_path,
        new_file_path)
    with open(todo_file_path, "a+") as todo:
        todo.write(output_string)


def executeToDoFile(todo_file_path):
    '''
    Function that runs each lines of todo.sh sequentially and erases them after
    Input: todo_file_path as string
    Ouptut: None
    '''
    os.chdir(script_root_dir)
    logger.info("Executing todo file")
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
        else:  # All the others
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
    with open(os.path.join(folder_info['path'], chapters_file), 'w') as file_list:
        file_list.write(output_string.encode('utf-8'))


def mount(remote_root_dir, ip_addr):
    '''
    Function that checks if remote media is mounted
    Input: remote_root_dir as string
    Output: Bool
    '''
    if (not os.path.exists(remote_root_dir)):
        logger.info('making dir {}'.format(remote_root_dir))
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
    except Exception:
        logger.info(traceback.format_exc())
        logger.info("Not mounted")
        return False


def checkIfVid(file_path):
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


def walk_path(local_root_dir):
    '''
    Function walks over folders
    '''
    for root, dirs, files in os.walk(local_root_dir, topdown=False):
        for name in files:
            print(os.path.join(root, name))
        for name in dirs:
            print(os.path.join(root, name))


def write_empty_config():
    '''
    Function that writes an empty config file
    Input: None
    Outpue: None
    '''
    #Create an empty file that you open
    with open(os.path.join(script_root_dir, 'empty_config.cfg'), 'w') as configFile:
        configFile.write("""######### CONFIG FILE
#Config file to pyHomeVM.
#FFMPEG, LOCAL and REMOTE are necessary.
#EMAIL and SMS are optional.
[FFMPEG]
ffmpegExecutablePath:
ffprobeExecutablePath:
vcodec:
acodec:
video_extensions:
ffmpeg_preset:
ffmpeg_crf:
ffmpeg_crf_base:

[LOCAL]
mkvmergeExecutablePath:
local_root_dir:
log_folder:
nas_composer_name:

[REMOTE]
ip_addr:
remote_root_dir:
remote_usr:
remote_pass:

[EMAIL]
mail_fromaddr:
mail_toaddrs:
mail_username:
mail_password:
mail_server_addr:

[SMS]
sms_path:
sms_user:
sms_password:
sms_api_id:
sms_to:

[HTML]
company_name:
company_mail:
company_phone:

[MEDIA]
logo_file:""")


def test_executable(path_to_exec):
    command = "which '{}'".format(path_to_exec)
    executeCommand(command)
    logger.info("'{}'' found".format(path_to_exec))


def build_html_report(html_data):
    '''
    Function that takes a dict with the folders that were
    modified/moved/created/deleted and replaces the values in the html files
    Input: html_data as dict
    Output: html_report as string
    '''
    #for action, values in html_data.items():
    header = html_header
    body = Template(html_body).safe_substitute(
        new_content=html_data['new'],
        modified_content=html_data['modified'],
        moved_content=html_data['moved'],
        deleted_content=html_data['deleted'])
    footer = Template(html_footer).safe_substitute(
        company_name=company_name,
        company_mail=company_mail,
        company_phone=company_phone)
    return(header + body + footer)

######## DONT LEAVE
video_extensions = ['mp4','mpg','mpeg','avi','tod','vob','wmv']

if __name__ == "__main__":
    #Main
    ##########################################################################
    #CONSTANTS
    script_root_dir = os.getcwd()
    todo_file_path = os.path.join(script_root_dir, 'todo.sh')
    dir_tree_file = os.path.join(script_root_dir, 'dir_tree.json')
    chapters_file = 'chapters.txt'
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(script_root_dir, 'log_{}.txt'.format(today))
    html_header = open(os.path.join(script_root_dir, 'html', 'header.html')).read()
    html_footer = open(os.path.join(script_root_dir, 'html', 'footer.html')).read()
    html_body = open(os.path.join(script_root_dir, 'html', 'body.html')).read()
    logo = os.path.join(script_root_dir, 'media', 'logo.png')
    ##########################################################################
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_file)
    #handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    parser = argparse.ArgumentParser(description='pyHomeVM')
    parser.add_argument('config_path',
                        help='path to config file that is to be used.')
    parser.add_argument('-s', '--sms', help='Enables sms notifications',
                        action='store_true')
    parser.add_argument('-l', '--log', help='Enables log sending by e-mail',
                        action='store_true')
    parser.add_argument('-r', '--report',
                        help='Enables html report sending by e-mail',
                        action='store_true')
    parser.add_argument('-b', '--backup',
                        help='Enables backup of first videos',
                        action='store_true')
    args = parser.parse_args()

    #Load configuration
    #def load_config(config_file):   
    config = ConfigParser.ConfigParser()
    config.optionxform = str  # Allows to keep upper case characters in config file
    if(os.path.exists(os.path.join(script_root_dir, args.config_path))):
        try:
            config.read(args.config_path)
            logger.info('{} found'.format(args.config_path))
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('{} not found\nProgram stopping'.format(args.config_path))
            exit()
        try:
            #FFMPEG
            ffmpegExecutablePath = config.get('FFMPEG', 'ffmpegExecutablePath')
            ffprobeExecutablePath = config.get('FFMPEG', 'ffprobeExecutablePath')
            vcodec = config.get('FFMPEG', 'vcodec')
            acodec = config.get('FFMPEG', 'acodec')
            video_extensions = config.get('FFMPEG', 'video_extensions').split(',')
            ffmpeg_preset = config.get('FFMPEG', 'ffmpeg_preset')
            ffmpeg_crf_base = config.getint('FFMPEG', 'ffmpeg_crf_base')
            logger.info('FFMPEG config loaded')
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('FFMPEG config could not be loaded\nProgram stopping')
            exit()
        try:
            #LOCAL
            local_root_dir = config.get('LOCAL', 'local_root_dir')
            log_folder = config.get('LOCAL', 'log_folder')
            nas_composer_name = config.get('LOCAL', 'nas_composer_name')
            mkvmergeExecutablePath = config.get('LOCAL', 'mkvmergeExecutablePath')
            logger.info('LOCAL config loaded')
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('LOCAL config could not be loaded\nProgram stopping')
            exit()
        try:
            #REMOTE
            ip_addr = config.get('REMOTE', 'ip_addr')
            remote_root_dir = config.get('REMOTE', 'remote_root_dir')
            remote_usr = config.get('REMOTE', 'remote_usr')
            remote_pass = config.get('REMOTE', 'remote_pass')
            logger.info('REMOTE config loaded')
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('REMOTE config could not be loaded\nProgram stopping')
            exit()
        try:
            #EMAIL
            mail_fromaddr = config.get('EMAIL', 'mail_fromaddr')
            mail_toaddrs = config.get('EMAIL', 'mail_toaddrs')
            mail_username = config.get('EMAIL', 'mail_username')
            mail_password = config.get('EMAIL', 'mail_password')
            mail_server_addr = config.get('EMAIL', 'mail_server_addr')
            logger.info('EMAIL config loaded')
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('EMAIL config could not be loaded\nProgram stopping')
            exit()
        if(args.sms):
            try:
                #SMS
                sms_path = config.get('SMS', 'sms_path')
                sms_user = config.get('SMS', 'sms_user')
                sms_password = config.get('SMS', 'sms_password')
                sms_api_id = config.get('SMS', 'sms_api_id')
                sms_to = config.get('SMS', 'sms_to')
                logger.info('SMS config loaded')
            except Exception:
                logger.info(traceback.format_exc())
                logger.info('SMS config could not be loaded\nProgram stopping')
                exit()
        if(args.report):
            try:
                #HTML
                company_name = config.get('HTML', 'company_name')
                company_mail = config.get('HTML', 'company_mail')
                company_phone = config.get('HTML', 'company_phone')
            except Exception:
                logger.info(traceback.format_exc())
                logger.info('HTML config could not be loaded\nProgram stopping')
                exit()

    else:
        write_empty_config()
        print('{} not found'.format(args.config_path))
        exit()

    ##########################################################################
    #Test if configs have been loaded correctly. Not fully done yet
    #for section in config.sections():
    for variable, value in config.items('FFMPEG'):
        #print(variable)
        if(variable == 'ffmpegExecutablePath' or
           variable == 'ffprobeExecutablePath'):
            try:
                test_executable(value)
            except Exception:
                logger.info(traceback.format_exc())
                logger.info('Executable {} not found'.format(variable))
    ###########################################################################
    try:  # Check to see if dir_tree exists -> program has been run already
        if not os.path.exists(dir_tree_file):
            raise Exception("Directory structure definition file not found.")
        past_structure = readStructureFromFile(dir_tree_file)  # Load past structure from file
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('{} not found'.format(dir_tree_file))
        past_structure = {}  # Start as new
    html_data = updateStructure(past_structure, readStructure(local_root_dir))
    #if(mount()):
    sms_sent_file = os.path.join(script_root_dir, 'sms_sent')
    if(True):
        if(os.path.isfile(todo_file_path)):
            executeToDoFile(todo_file_path)
        syncDirTree()
        transferLongVersions()
        if(os.path.exists(sms_sent_file)):
            os.remove(sms_sent_file)
            logger.info('sms_sent file has been deleted')
    else:
        if(not os.path.exists(sms_sent_file)):
            sendSmsNotification('Le NAS veut transférer des fichier sur le media center. Veuillez allumer le media center svp')
            with open(sms_sent_file, 'w') as sms_not:
                msg = 'SMS has been sent {}'.format(today)
                sms_not.write(msg)
                logger.info(msg)
    if(args.report and
            html_data['new'] != '' or
            html_data['modified'] != '' or
            html_data['deleted'] != '' or
            html_data['moved'] != ''):
        html_report = build_html_report(html_data)
        sendMailReport(html_report)
    if(args.log):
        sendMailLog(log_file)
        pass


# future module: http://code.activestate.com/recipes/577376-simple-way-to-execute-multiple-process-in-parallel/