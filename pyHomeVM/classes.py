# coding=utf-8
import logging
from CONSTANTS import CONSTANTS
import os
import time
import json
import traceback
from commands import executeCommand


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(CONSTANTS['log_file_path'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Video(object):
    def __init__(self, file_id, file_path, category):
        self.file_path = file_path
        self.file_id = file_id
        self.file_name = os.path.basename(file_path)
        self.duration = None
        self.offset = None
        self.video_codec = None
        self.audio_codec = None
        self.composer = None
        self.height = None
        self.width = None
        self.frame_rate = None
        self.creation_time = None
        self.category = category

    def populate_video_details(self, local):
        command = (
            "'{}' -v quiet -show_format "
            "-show_streams -print_format json "
            "-sexagesimal '{}'").format(
            local['ffprobe_executable_path'],
            self.file_path.encode('utf-8'))
        stdout, err = executeCommand(command)
        stdout = json.loads(stdout)
        streams = stdout.get('streams')
        for stream_num, stream in enumerate(streams):
            if(stdout['streams'][stream_num]['codec_type'] == 'video'):
                video = stdout['streams'][stream_num]
                self.height = video.get('height')
                self.width = video.get('width')
                self.duration = video.get('duration')
                self.offset = video.get('start_time')
                self.video_codec = video.get('codec_name')
                self.frame_rate = video.get('r_frame_rate')

            if(stdout['streams'][stream_num]['codec_type'] == 'audio'):
                audio = stdout['streams'][stream_num]
                self.audio_codec = audio.get('codec_name')
        self.video_type = "{}{}{}{}{}".format(
            self.audio_codec,
            self.video_codec,
            str(self.width),
            str(self.height),
            str(self.frame_rate))
        formats = stdout.get('format')
        try:
            tags = formats.get('tags')
            self.composer = tags.get('composer')
            self.creation_time = tags.get('creation_time')
        except Exception:
            logger.info(traceback.format_exc())
            logger.info("No tags in {}".format(self.file_path))

    def baseConvertVideo(self, ffmpeg, local, output_file):
        #temp_path = os.path.join(os.path.dirname(self.file_path), 'temp.vid')
        #os.rename(self.file_path, temp_path)
        if(self.composer):
            composer = self.composer
        else:
            composer = ffmpeg['composer_name']
        if(self.creation_time):
            creation_time = self.creation_time
        else:
            creation_time = time.strftime('%Y-%m-%d %H:%M:%S')
        #output_file = os.path.splitext(self.file_path)[0] + '.mp4'
        command = (
            "'{}' -loglevel panic -y -i '{}' "
            "-rc_eq 'blurCplx^(1-qComp)' "
            "-c:v {} -c:a {} -preset {} -crf {} "
            "-metadata composer={} -metadata creation_time='{}' "
            "-movflags +faststart -pix_fmt yuv420p "
            "-profile:v high -level 3.1 '{}'").format(
            local['ffmpeg_executable_path'],
            self.file_path,
            ffmpeg['vcodec'],
            ffmpeg['acodec'],
            ffmpeg['preset'],
            ffmpeg['crf'],
            composer,
            creation_time,
            output_file)
        executeCommand(command)
        #return(output_file)
        #os.remove(temp_path)

    def convertVideo(self, ffmpeg, local, formats, compatibility_folder_path):
        #input_file = os.path.join(compatibility_folder, os.path.basename(self.file_path))
        #os.rename(self.file_path, input_file)
        output_file = os.path.join(
            compatibility_folder_path,
            os.path.splitext(os.path.basename(self.file_path))[0] + '.mp4')
        command = (
            "'{}' -loglevel panic -y -i '{}' "
            "-rc_eq 'blurCplx^(1-qComp)' "
            "-vf scale={}:{} -r {} -c:v {} -c:a {} -preset {} -crf {} "
            "-metadata composer={} -metadata creation_time='{}' "
            "-movflags +faststart -pix_fmt yuv420p "
            "-profile:v high -level 3.1 '{}'").format(
            local['ffmpeg_executable_path'],
            self.file_path.encode('utf-8'),
            formats['width'],
            formats['height'],
            formats['frame_rate'],
            ffmpeg['vcodec'],
            ffmpeg['acodec'],
            ffmpeg['preset'],
            ffmpeg['crf'],
            self.composer,
            self.creation_time,
            output_file.encode('utf-8'))
        executeCommand(command)
        return(output_file)
