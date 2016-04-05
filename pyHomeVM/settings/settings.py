import logging
import os
import ConfigParser
import traceback
from .. import CONSTANTS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(CONSTANTS.CONSTANTS['log_file_path'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def load_core(config):
    logger.info('Local and ffmpeg loading')
    ffmpeg = {}
    local = {}
    try:
        # FFMPEG
        vcodec = config.get('FFMPEG', 'vcodec')
        acodec = config.get('FFMPEG', 'acodec')
        preset = config.get('FFMPEG', 'preset')
        crf = config.getint('FFMPEG', 'crf_base')
        composer_name = config.get('FFMPEG', 'composer_name')
        logger.info('FFMPEG config loaded')
        # LOCAL
        ffprobe_executable_path = config.get('LOCAL', 'ffprobe_executable_path')
        ffmpeg_executable_path = config.get('LOCAL', 'ffmpeg_executable_path')
        video_extensions = config.get('LOCAL', 'video_extensions').split(',')
        root_dir = config.get('LOCAL', 'root_dir')
        log_folder = config.get('LOCAL', 'log_folder')
        mkvmerge_executable_path = config.get('LOCAL', 'mkvmerge_executable_path')
        logger.info('LOCAL config loaded')
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('Core config could not be loaded. Program stopping')
        exit()
    ffmpeg['vcodec'] = vcodec
    ffmpeg['acodec'] = acodec
    ffmpeg['preset'] = preset
    ffmpeg['crf'] = crf
    ffmpeg['composer_name'] = composer_name
    local['ffmpeg_executable_path'] = ffmpeg_executable_path
    local['ffprobe_executable_path'] = ffprobe_executable_path
    local['video_extensions'] = video_extensions
    local['root_dir'] = root_dir
    local['log_folder'] = log_folder
    local['mkvmerge_executable_path'] = mkvmerge_executable_path
    logger.info('ffmpeg and local loaded')
    return(ffmpeg, local)


def load_remote(config):
    logger.info('Remote loading')
    remote = {}
    try:
        ip_addr = config.get('REMOTE', 'ip_addr')
        root_dir = config.get('REMOTE', 'root_dir')
        username = config.get('REMOTE', 'username')
        password = config.get('REMOTE', 'password')
        logger.info('REMOTE config loaded')
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('REMOTE config could not be loaded')
    remote['ip_addr'] = ip_addr
    remote['root_dir'] = root_dir
    remote['username'] = username
    remote['password'] = password
    logger.info('Remote loaded')
    return(remote)


def load_email(config):
    logger.info('EMAIL loading')
    email = {}
    try:
        from_adr = config.get('EMAIL', 'from')
        to = config.get('EMAIL', 'to')
        username = config.get('EMAIL', 'username')
        password = config.get('EMAIL', 'password')
        server_address = config.get('EMAIL', 'server_address')
        logger.info('EMAIL config loaded')
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('EMAIL config could not be loaded')
    email['from'] = from_adr
    email['to'] = to
    email['username'] = username
    email['password'] = password
    email['server_address'] = server_address
    logger.info('EMAIL loaded')
    return(email)


def load_html(config):
    logger.info('HTML loading')
    html = {}
    try:
        company_name = config.get('HTML', 'company_name')
        company_mail = config.get('HTML', 'company_mail')
        company_phone = config.get('HTML', 'company_phone')
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('HTML config could not be loaded')
    html['company_name'] = company_name
    html['company_mail'] = company_mail
    html['company_phone'] = company_phone
    logger.info('HTML loaded')
    return(html)


def load_sms(config):
    logger.info('SMS loading')
    sms = {}
    try:
        server_address = config.get('SMS', 'server_address')
        username = config.get('SMS', 'username')
        password = config.get('SMS', 'password')
        api_id = config.get('SMS', 'api_id')
        to = config.get('SMS', 'to')
        logger.info('SMS config loaded')
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('SMS config could not be loaded')
    sms['server_address'] = server_address
    sms['username'] = username
    sms['password'] = password
    sms['api_id'] = api_id
    sms['to'] = to
    logger.info('SMS loaded')
    return(sms)


def load_config(config_file_path):
    logger.info('Root config loading')
    config = ConfigParser.ConfigParser()
    config.optionxform = str  # Allows to keep upper case characters in config file
    config_file_path = os.path.join(CONSTANTS.CONSTANTS['script_root_dir'], config_file_path)
    if(os.path.exists(config_file_path)):
        try:
            config.read(config_file_path)
            logger.info('{} found'.format(config_file_path))
        except Exception:
            logger.info(traceback.format_exc())
            logger.info('{} not found. Program stopping'.format(config_file_path))
            exit()
    else:
        new_config = raw_input('No config file found. Do wou want to create an empty one? (Y/N): ')
        if(new_config in ('Y', 'y', 'yes', 'YES')):
            config_file_name = raw_input('Please enter a configuration file name: ')
            write_empty_config(config_file_name)
        exit()
    logger.info('Root config loaded')
    return(config)


def write_empty_config(config_file_name):
    """
    Function that writes an empty config file
    Input: None
    Outpue: None
    """
    # Create an empty file that you open
    with open(os.path.join(
            CONSTANTS.CONSTANTS['script_root_dir'],
            'pyHomeVM',
            'settings',
            '{}.cfg'.format(config_file_name.rstrip('.cfg'))), 'w') as configFile:
        configFile.write("""######### CONFIG FILE
# Here you have to specify your video root directory, your media center root path,
# ffmpeg, ffprob and mkvmerge executable paths. All in absolute
# Example
[FFMPEG]
vcodec:
acodec:
preset:
crf_base:
composer_name:

[LOCAL]
ffmpeg_executable_path:
ffprobe_executable_path:
video_extensions:
mkvmerge_executable_path:
root_dir:
log_folder:

[REMOTE]
ip_addr:
root_dir:
username:
password:

[EMAIL]
from:
to:
username:
password:
server_address:

[SMS]
server_address:
username:
password:
api_id:
to:
scheduled_time:

[HTML]
company_name:
company_mail:
company_phone:

[MEDIA]
logo_file:""")
