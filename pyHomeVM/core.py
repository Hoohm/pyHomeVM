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
import traceback
import shutil
from string import Template
from CONSTANTS import CONSTANTS
from classes import Video
from commands import executeCommand


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(CONSTANTS['log_file_path'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def create_file_id(file_path, block_size=256):
    '''
    Function that takes a file and returns the first 10 characters of a hash of
    the first 10 block of bytes
    Input: File
    Output: Hash of 10 blocks of 128 bits of size as string
    '''
    file_size = os.path.getsize(file_path)
    start_index = int(file_size / 2)
    with open(file_path, 'r') as f:
        f.seek(start_index)
        n = 1
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            n += 1
            if (n == 10):
                break
            md5.update(data)
    return("{}{}".format(md5.hexdigest()[0:9], str(file_size)))


def create_folder_id(folder_path, local):
    '''
    Function that takes a folder path and returns a unique ID to
    identify a specific content of folder.
    Input: folder_path as string
    Output: ID as string
    '''
    folder_id = ''
    video_list = {}
    for file_name in sorted(list_video_files(folder_path, local)):  # loop files
        cur_path = os.path.join(folder_path, file_name)
        file_id = create_file_id(cur_path)
        video_list[file_id] = file_name.decode('utf-8')
        folder_id += file_id
    return(folder_id, video_list)


def list_video_files(folder_path, local):
    '''
    Function that lists the video files found in a folder
    Input: folder_path as string
    Output: list of videos paths (as strings)
    '''
    return [i
            for i in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, i))
            and
            check_if_vid(os.path.join(folder_path, i), local)]


def check_mkv_videos(local, video_db):
    '''
    Function that checks that all mkvs long videos have
    the same name than their folder
    '''

    # for video_id in video_db.keys():
    #     if(video_db[video_id].category == 'long'):
    #         if(local['root_dir'] in video_db[video_id].file_path):
    #             if(os.path.isfile(video_db[video_id].file_path)):
    #                 continue
    #             else:
    #                 old_path = video_db[file_id]
    #                 #new_path = 
    #                 os.rename(video_db[video_id].file_path, )
    root_dir = local['root_dir']
    for i in os.walk(root_dir):
        if(len(i[0].split('/')) - 2 == len(root_dir.split('/'))  # 2 levels
                and re.match(r'^[0-9]{4}$', i[0].split('/')[-2])  # match year
                and len(i[2]) != 0):  # is not empty
            for video in i[2]:
                if(os.path.splitext(video)[1] == '.mkv'):
                    file_path = os.path.join(i[0], video)
                    ID = create_file_id(file_path)
                    if(video_db[ID].file_path != file_path):
                        os.rename(
                            file_path,
                            os.path.join(os.path.dirname(file_path),
                            os.path.dirname(file_path).split('/')[-1]) + '.mkv')
                        video_db[ID].file_path = file_path



def write_structure(structure, file_path):
    '''Function that writes a dir structure to dir_tree.json file
    Input: structure as dict, file_path as string
    Output: None
    '''
    with open(file_path, 'w') as outfile:
        json.dump(structure, outfile)


def convert_keys_to_string(dictionary):
    """
    Recursively converts dictionary keys to strings.
    """
    if not isinstance(dictionary, dict):
        return dictionary
    return dict((str(k), convert_keys_to_string(v))
                for k, v in dictionary.items())


def readStructureFromFile(CONSTANTS):
    '''
    Function that reads a structure file from a json file
    Input: file_path as string dir_tree.json
    Output: structure as dict
    '''
    with codecs.open(CONSTANTS['structure_file_path'], 'r', 'utf-8') as f:
        try:
            structure = json.load(f)
        except Exception:
            logger.info(traceback.format_exc())
            return {}
    converted_structure = convert_keys_to_string(structure)
    return(converted_structure)


def createStructureEntry(ID, structure, folder_path, video_list):
    '''
    Function that creates an entry in the structure object
    Input: ID, structure, folder_path, video_list
    Output: NA, changes strucure in place'''
    structure[ID] = {}
    structure[ID]['path'] = folder_path
    structure[ID]['video_list'] = video_list


def get_new_file_ids_from_structure(structure, video_db):
    '''
    Function that lists the videos that are in a structure
    and looks for them in the video.db file.
    Returns the list of videos found in structure but not in the db,
    meaning they are new.
    Input:  - structure as dict
            - video_db as shelve object
    Output: dict with file_id as keys and file_path as values
    '''
    video_ids = {}
    for folder_id in structure.keys():
        for file_id, file_name in structure[folder_id]['video_list'].items():
            if(file_id not in video_db.keys()):
                video_ids[file_id] = os.path.join(
                    structure[folder_id]['path'],
                    file_name)
    return(video_ids)


def check_and_correct_videos_errors(video_ids, video_db, local, ffmpeg):
    '''
    Function that loops through a list of video ids, uses checkVideoIntegrity
    to checks if they contain errors or are corrupted
    and calls correct_video on them.
    Input:  - video_ids as list of video ids
            - video_db as shelve object
            - local as local config dict
            - ffmpeg as ffmpeg config dict
    Ouput: NA
    '''
    for file_id in video_ids.keys():
        state = checkVideoIntegrity(
            video_ids[file_id],
            file_id,
            local,
            video_db)
        correct_video(state, video_ids[file_id], file_id, local, ffmpeg)


def correct_video(state, file_path, file_id, local, ffmpeg):
    '''
    Function that deals with errors in videos or corrupted videos.
    '''
    folder_path = os.path.dirname(file_path)
    if(state == 'corrupt'):  # Move the file into corrupted folder
        if(not os.path.exists(os.path.join(folder_path, 'corrupted'))):
            os.makedirs(os.path.join(folder_path, 'corrupted'))
        os.rename(
            file_path,
            os.path.join(folder_path, 'corrupted', os.path.basename(file_path)))
    elif(state == 'error'):  # Reencode
        if(not os.path.exists(os.path.join(folder_path, 'errors'))):
            os.makedirs(os.path.join(folder_path, 'errors'))
        new_file_path = os.path.join(
            folder_path, 'errors',
            os.path.basename(file_path))
        os.rename(file_path, new_file_path)
        temp_vid = Video(file_id, new_file_path, category='error')
        temp_vid.populate_video_details(local)
        temp_vid.baseConvertVideo(
            ffmpeg,
            local,
            os.path.splitext(file_path)[0] + '.mp4')


def read_structure(local):
    '''
    Function that reads the structure of the dirs of the videos
    Input: Base dirs as lit
    Output: Dict of dir structure of videos

    '''
    structure = {}
    root_dir = local['root_dir']
    for i in os.walk(root_dir):
        if(len(i[0].split('/')) - 2 == len(root_dir.split('/'))  # 2 levels
                and re.match(r'^[0-9]{4}$', i[0].split('/')[-2])  # match year
                and len(i[2]) != 0):  # is not empty
            ID, video_list = create_folder_id(i[0], local)
            if(ID == ''):
                continue
            else:
                createStructureEntry(
                    ID,
                    structure,
                    i[0].decode('utf-8'),
                    video_list)
    return(structure)


def clean_video_db(video_db):
    '''
    Checks for videos that belong to any other category than normal
    and deletes them from the db
    Input:  - video_db as shelve object
    Output: NA
    '''
    for file_id in video_db:
        if(video_db[file_id].category == 'normal'
                or video_db[file_id].category == 'long'):
            pass
        else:
            del(video_db[file_id])


def multiple_formats(video_list, video_db):
    '''
    Function that verifies the string of options from a list
    of video. If there are more than 1 return True
    Input:  - video list
            - video db
    Output: - Bool
    '''
    video_types = {}
    for file_id in video_list:
        video_types[video_db[file_id].video_type] = 0
    if(len(video_types) > 1):
        return(True)
    return(False)


def choose_format(video_list, video_db):
    '''
    Function that selects the resolution and frame rate
    for the long version
    Input:  - video list of video ids
            - video db
    Output: - dict with framerate and resolution
    '''
    widths = []
    heights = []
    frame_rates = []
    for file_id in video_list:
        widths.append(video_db[file_id].width)
        heights.append(video_db[file_id].height)
        frame_rates.append(video_db[file_id].frame_rate)
    formats = {
        'width': min(widths),
        'height': heights[widths.index(min(widths))],  # Keep aspect ratio
        'frame_rate': min(frame_rates),
        'video_codec': 'h264',
        'audio_codec': 'aac'}
    return(formats)


def checkDetailsCompatibility(structure, folder_id, video_db, ffmpeg, local, remote):
    '''
    Function that checks that every video in one folder have the same
    resolution or framerate.
    If not, converts to the lowest standard of the different possibilities.
    Input: folder_info as dict of video details
    Output: changes as Bool
    '''
    videos = structure[folder_id]['video_list'].keys()
    video_list = []
    if(multiple_formats(videos, video_db)):
        comp_folder = os.path.join(
            structure[folder_id]['path'],
            'compatibility')
        os.makedirs(comp_folder)
        formats = choose_format(videos, video_db)
        for file_id in videos:
            if(video_db[file_id].frame_rate != formats['frame_rate'] or
                    video_db[file_id].width != formats['width'] or
                    video_db[file_id].height != formats['height'] or
                    video_db[file_id].video_codec != formats['video_codec'] or
                    video_db[file_id].audio_codec != formats['audio_codec']):
                target_file_path = video_db[file_id].convertVideo(
                    ffmpeg,
                    local,
                    formats,
                    comp_folder)
                temp_file_id = create_file_id(target_file_path)
                video_db[temp_file_id] = Video(
                    temp_file_id,
                    target_file_path,
                    'compatibility')
                video_db[temp_file_id].populate_video_details(local)
                video_list.append(temp_file_id)
            else:
                video_list.append(file_id)
    else:
        video_list = videos
    sorted_video_list = get_video_order(video_list, video_db, by='file_name')
    createChaptersList(structure[folder_id]['path'], video_db, sorted_video_list)
    createLongVideo(structure[folder_id]['path'], sorted_video_list, local, remote, video_db)
    try:
        shutil.rmtree(comp_folder)
    except:
        pass


def get_video_order(file_ids, video_db, by):
    video_path_list = {}
    sorted_ids = []
    if(by == 'file_name'):
        for file_id in file_ids:
            video_path_list[video_db[file_id].file_name] = file_id
    elif(by == 'creation_time'):
        for file_id in file_ids:
            video_path_list[video_db[file_id].creation_time] = file_id
    for i in sorted(video_path_list):
        sorted_ids.append(video_path_list[i])
    return(sorted_ids)


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
        microseconds=t1.microsecond)
    deltat2 = timedelta(
        hours=t2.hour,
        minutes=t2.minute,
        seconds=t2.second,
        microseconds=t2.microsecond)
    return(deltat1 + deltat2)


def format_html(old_path, present_path, action, **file_paths):
    '''
    Function that takes two paths, and action and file lists
    and returns an html string that will be inserted in html_report
    Input: old_path as string, present_path as string, action as string
    file_paths as dict of files as string
    '''
    if(action == 'moved'):
        html_string = 'Le dossier <b>{}</b> en {} a été déplacé en {} sous <b>{}</b><br>'.format(
            old_path.split('/')[-1],
            old_path.split('/')[-2],
            present_path.split('/')[-1],
            present_path.split('/')[-2])
    if(action == 'modified'):
        html_string = 'Ce dossier a été modifié: <b>{}</b> en {}<br>'.format(
            present_path.encode('utf-8').split('/')[-1],
            present_path.encode('utf-8').split('/')[-2])
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
            present_path.split('/')[-1],
            present_path.split('/')[-2])
    if(action == 'new'):
        html_string = 'Le dossier <b>{}</b> en {} est nouveau<br><br>'.format(
            present_path.encode('utf-8').split('/')[-1],
            present_path.encode('utf-8').split('/')[-2])
    return(html_string)


def updateStructure(past_structure, new_structure, local, ffmpeg, remote, video_db):
    '''
    Function that compares two structures looking
    for new,modified,deleted folders/files
    Input: past_structure as dict, new_structure as dict
    Output: None, changes strucure in place
    '''
    html_report = {'new': '', 'modified': '', 'moved': '', 'deleted': ''}
    if(new_structure == past_structure):
        return(html_report)
    new_paths = getPathList(new_structure)
    new_file_ids = set()
    for struct_id in new_structure:
        for file_id in new_structure[struct_id]['video_list']:
            new_file_ids.add(file_id)
    a = set(video_db.keys())
    b = new_file_ids
    diff = a - b
    for file_id in diff:
        if(video_db[file_id].category != 'long'):
            del(video_db[file_id])
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
                for file_id, file_name in new_structure[ID]['video_list'].items():
                    video_db[file_id].file_path = os.path.join(new_path.decode('utf-8'), file_name)
                present_structure[ID]['path'] = new_structure[ID]['path']
                if(not mkv_in_local(past_structure[ID]['path'], present_structure[ID]['path'])):
                    moveLongVideo(past_structure[ID]['path'], present_structure[ID]['path'], local, remote)
        else:  # Hash missing in the new struct. Deleted or modified
            if(past_structure[ID]['path'] in new_paths):  # Modified
                folder_path = past_structure[ID]['path']
                logger.info('[MODIFIED] {}'.format(folder_path.encode('utf-8')))
                new_files = [
                    new for new in list_video_files(folder_path, local)
                    if new not in past_structure[ID]['video_list'].values()]
                del_files = [
                    deleted for deleted in past_structure[ID]['video_list'].values()
                    if deleted not in list_video_files(folder_path, local)]
                html_report['modified'] += format_html('', folder_path, action='modified', new_files=new_files, del_files=del_files)
                new_ID, video_list = create_folder_id(folder_path.encode('utf-8'), local)
                present_structure = process_folder(
                    new_structure,
                    present_structure,
                    new_ID,
                    video_db,
                    ffmpeg,
                    local,
                    remote)
                del(present_structure[ID])
            else:  # No hash and no path -> Deleted
                folder_path = past_structure[ID]['path'].encode('utf-8')
                logger.info("[DELETED]  {}".format(folder_path))
                html_report['deleted'] += format_html('', folder_path, action='deleted')
                del present_structure[ID]
        write_structure(present_structure, CONSTANTS['structure_file_path'])
    present_paths = getPathList(present_structure)  # Get list pf paths
    for new_ID in new_structure.keys():
        if(new_ID not in present_structure.keys() and new_structure[new_ID]['path'] not in present_paths):
            folder_path = new_structure[new_ID]['path']
            logger.info("[NEW]   {}".format(folder_path.encode('utf-8')))
            html_report['new'] += format_html('', folder_path, action='new')
            present_structure = process_folder(
                new_structure,
                present_structure,
                new_ID,
                video_db,
                ffmpeg,
                local,
                remote)
        write_structure(present_structure, CONSTANTS['structure_file_path'])
    logger.info('Structure updated')
    return(html_report)


def mkv_in_local(old_path, new_path):
    new_file_path = os.path.join(new_path, os.path.basename(old_path) + '.mkv')
    print(new_file_path)
    if(os.path.exists(new_file_path)):
        return(True)
    else:
        return(False)


def process_folder(structure, present_structure, folder_id, video_db, ffmpeg, local, remote):
    folder_path = structure[folder_id]['path']
    createStructureEntry(
        folder_id,
        present_structure,
        folder_path,
        structure[folder_id]['video_list'])
    for file_id, file_name in present_structure[folder_id]['video_list'].items():
        state = (file_id in video_db)
        updateVideoDB(video_db, ffmpeg, local, file_id, file_name, state, folder_path)
    checkDetailsCompatibility(present_structure, folder_id, video_db, ffmpeg, local, remote)
    return(present_structure)


def updateVideoDB(video_db, ffmpeg, local, file_id, file_name, state, folder_path):
    '''
    Updates video db with the new videos.
    '''
    if(not state):  # Store
        temp_vid = Video(
            file_id,
            os.path.join(folder_path, file_name),
            category='normal')
        temp_vid.populate_video_details(local)
        video_db[temp_vid.file_id] = temp_vid
    else:  # Already in our video DB
        video_db[file_id].file_path = os.path.join(folder_path, file_name)


def video_in_db(video_db, file_id):
    if(file_id in video_db):
        return('exists')
    else:
        return('new')


def checkVideoIntegrity(file_path, file_id, local, video_db):
    '''
    Checks if video is corrupted or contains errors
    '''
    cmd = "'{}' -v error -i '{}' -f null -".format(
        local['ffmpeg_executable_path'],
        file_path.encode('utf-8'))
    (stdout, err) = executeCommand(cmd)
    if(re.findall('Invalid data found when processing input', err)):
        return('corrupt')
    elif(err != ''):
        return('error')
    else:
        return('clean')


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


def syncDirTree(local, remote):
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
            "{} {}").format(local['root_dir'] + '/', remote['root_dir'] + '/'))


def transferLongVersions(local, remote, video_db):
    '''
    Function that looks for mkv movies and sends them
    to the remote media player
    Input: None
    Output: None
    '''
    long_videos_path = []
    root_dir = local['root_dir']
    for i in os.walk(root_dir):
        if(len(i[0].split('/')) - 2 == len(root_dir.split('/'))  # 2 levels
                and re.match(r'^[0-9]{4}$', i[0].split('/')[-2])  # match year
                and len(i[2]) != 0):
            for video in i[2]:
                if(os.path.splitext(video)[1] == '.mkv'
                        and os.path.splitext(video)[0] == os.path.basename(i[0])):
                    long_videos_path.append(os.path.join(i[0], video))
    for video in long_videos_path:
        #  if(os.splitext(video_db[create_file_id(video)].file_name)[0] == ):
        try:
            os.rename(
                video,
                os.path.join(video.replace(local['root_dir'], remote['root_dir'])))
        except Exception:
            logger.info(traceback.format_exc())
    logger.info("Long versions have been moved to remote")


def createLongVideo(folder_path, video_list, local, remote, video_db):
    '''
    Function that runs mkvmerge to create a long version of list of videos.
    Needs a chapter file (see createChaptersList)
    Input: folder_info as dict
    Ouptut: None
    '''
    file_in = ''
    if(len(video_list) == 1):  # Only one video
        file_in += video_db[video_list[0]].file_path
    else:
        for file_id in video_list:
            file_in += "'{}' + ".format(
                video_db[file_id].file_path.encode('utf-8')) # .replace(' ', '\ ')
        file_in = file_in.rstrip(' + ')
    chapters_file_path = os.path.join(
        folder_path, CONSTANTS['chapters_file_name'])
    output_file = os.path.join(
        folder_path.encode('utf-8'),
        os.path.basename(folder_path.encode('utf-8')) + '.mkv')
    command = "{} {} --quiet --chapters '{}' -o '{}'".format(
        local['mkvmerge_executable_path'].encode('utf-8'),
        file_in,
        os.path.join(
            folder_path,
            chapters_file_path).encode('utf-8'),#.replace(' ', '\ '),
        output_file)
    stdout, err = executeCommand(command)
    output_file_id = create_file_id(output_file)
    video_db[output_file_id] = Video(
        output_file_id,
        output_file,
        category='long')
    # video_db[output_file_id].remote_file_path = output_file.replace(
    #     local['root_dir'],
    #     remote['root_dir'])
    os.remove(chapters_file_path)


def clean_remote(remote):
    for i in os.walk(remote['root_dir']):
        if(len(i[2]) == 0 and len(i[1]) == 0):
            os.rmdir(i[0])

    for i in os.walk(remote['root_dir']):
        if(len(i[2]) == 0 and len(i[1]) == 0):
            os.rmdir(i[0])


def moveLongVideo(old_path, new_path, local, remote):
    '''
    Function that adds bash commands to move files on the remote storage
    as strings into a file (default = /share/Scripts/todo.sh)
    Input: old_path as string, new_path as string, todo_file_path as string
    Ouptut: None
    '''
    output_string = ''
    old_file_path = "{}/{}.mkv".format(
        os.path.join(
            old_path.replace(local['root_dir'], remote['root_dir'])).encode('utf-8'),
        os.path.basename(old_path).encode('utf-8'))
    new_file_path = "{}/{}.mkv".format(
        os.path.join(new_path.replace(local['root_dir'], remote['root_dir'])).encode('utf-8'),
        os.path.basename(new_path).encode('utf-8'))
    #  new_folder_path = new_path.replace(local['root_dir'], remote['root_dir'])
    #  output_string += "mkdir '{}'\n".format(new_folder_path.encode('utf-8'))
    output_string += "mv '{}' '{}'\n".format(
        old_file_path,
        new_file_path)
    with open(CONSTANTS['todo_file_path'], "a+") as todo:
        todo.write(output_string)


def executeToDoFile(todo_file_path, local, CONSTANTS):
    '''
    Function that runs each lines of todo.sh sequentially and erases them after
    Input: todo_file_path as string
    Ouptut: None
    '''
    os.chdir(local['root_dir'])
    logger.info("Executing todo file")
    while 1:
        with open(CONSTANTS['todo_file_path'], 'r') as f:
            first = f.readline()
            logger.info(first)
            if(first == ''):
                break
            sub = subprocess.Popen(first, shell=True)
            sub.wait()
            if(sub.wait() != 0):
                logger.info(sub.wait())
        out = subprocess.Popen(
            "sed '1d' '{}' > '{}'/tmpfile; mv tmpfile '{}'".format(
                CONSTANTS['todo_file_path'],
                local['root_dir'],
                CONSTANTS['todo_file_path']), shell=True)
        out.wait()
    logger.info("Todo file done")
    os.remove(CONSTANTS['todo_file_path'])


def createChaptersList(folder_path, video_db, video_list):
    '''
    Function that creates a file containning the video list and the duration of
    the videos to pass to mkvmerge to create a long version with chapters
    Input: folder_info as dict
    Ouptut: None
    '''
    time_format = re.compile('([0-9]{1,2}:[0-9]{2}:[0-9]{2}.[0-9]{3})')
    output_string = ''
    for n, file_id in enumerate(video_list):
        if (n == 0):  # First Video
            output_string += 'CHAPTER{}={}\nCHAPTER{}NAME={}\n'.format(
                n,
                re.search(time_format, video_db[file_id].offset).group(1),
                n,
                os.path.splitext(video_db[file_id].file_name)[0].encode('utf-8'))
            last = addTime(
                video_db[file_id].duration,
                video_db[file_id].offset)
        else:  # All the others
            o = datetime.strptime(video_db[file_id].offset, '%H:%M:%S.%f')
            delta0 = timedelta(
                hours=o.hour,
                minutes=o.minute,
                seconds=o.second,
                microseconds=o.microsecond)
            output_string += 'CHAPTER{}={}\nCHAPTER{}NAME={}\n'.format(
                n,
                re.search(time_format, datetimeToStr(delta0 + last)).group(1),
                n,
                os.path.splitext(video_db[file_id].file_name)[0].encode('utf-8'))
            last = addTime(video_db[file_id].duration, datetimeToStr(last))
    with open(os.path.join(folder_path, CONSTANTS['chapters_file_name']), 'w') as file_list:
        file_list.write(output_string)


def mount(remote):
    '''
    Function that checks if remote media is mounted
    Input: remote['root_dir'] as string
    Output: Bool
    '''
    if (not os.path.exists(remote['root_dir'])):
        logger.info('making dir {}'.format(remote['root_dir']))
        os.makedirs(remote['root_dir'])
    try:
        proc = subprocess.Popen(
            "mount -t cifs //{}{} -o username={},password={} {}".format(
                remote['ip_addr'],
                remote['root_dir'],
                remote['username'],
                remote['password'],
                remote['root_dir'])
        )
        stdout, err = proc.communicate()
        if proc.wait() == 0:
            logger.info("Mounted!")
            return True
    except Exception:
        logger.info(traceback.format_exc())
        logger.info("Not mounted")
        return False


def check_if_vid(file_path, local):
    '''
    Function that checks if a file a video with known extension
    Input: file_path as string, video_extensions as list of strings
    Ouptut: Bool
    '''
    for ext in local['video_extensions']:
        if(file_path.endswith(ext) or file_path.endswith(ext.upper())):
            return True
    else:
        return False


def build_html_report(html_data, CONSTANTS, html):
    '''
    Function that takes a dict with the folders that were
    modified/moved/created/deleted and replaces the values in the html files
    Input: html_data as dict
    Output: html_report as string
    '''
    # for action, values in html_data.items():
    header = open(CONSTANTS['html_header_path']).read()
    body = Template(open(CONSTANTS['html_body_path']).read()).safe_substitute(
        new_content=html_data['new'],
        modified_content=html_data['modified'],
        moved_content=html_data['moved'],
        deleted_content=html_data['deleted'])
    footer = Template(open(CONSTANTS['html_footer_path']).read()).safe_substitute(
        company_name=html['company_name'],
        company_mail=html['company_mail'],
        company_phone=html['company_phone'])
    return(header + body + footer)

# future module: http://code.activestate.com/recipes/577376-simple-way-to-execute-multiple-process-in-parallel/
