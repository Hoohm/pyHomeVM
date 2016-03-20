"""__Main__."""
import sys
import os
import logging
import argparse
import traceback
import shelve
from datetime import datetime
from CONSTANTS import CONSTANTS
from settings.settings import load_config, load_core, load_remote, load_email
from settings.settings import load_html, load_sms
from core import read_structure, readStructureFromFile, updateStructure
from core import clean_video_db, syncDirTree, transferLongVersions
from core import executeToDoFile, build_html_report, umount
from core import check_and_correct_videos_errors, clean_remote
from core import get_new_file_ids_from_structure, mount, check_mkv_videos
from notifications import sendSmsNotification, sendMailReport, sendMailLog


def get_args():
    """Get args."""
    parser = argparse.ArgumentParser(description='pyHomeVM')
    parser.add_argument('-c', '--config_file_path',
                        action='store',
                        default='settings/dev_config.cfg',
                        help='path to config file that is to be used.')
    parser.add_argument('-s', '--sms', help='Enables sms notifications',
                        action='store_true')
    parser.add_argument('-l', '--log', help='Enables log sending by e-mail',
                        action='store_true')
    parser.add_argument('-r', '--report',
                        help='Enables html report sending by e-mail',
                        action='store_true')
    parser.add_argument('-rem', '--remote',
                        help='Enables transfer of long versions to remote storage',
                        action='store_true')
    parser.add_argument('-b', '--backup',
                        help='Enables backup of first videos',
                        action='store_true')
    parser.add_argument('-stats',
                        help='Gets you statistics about your videos',
                        action='store_true')
    args = parser.parse_args()
    return args


def load_logger():
    """Load logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(CONSTANTS['log_file_path'])
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def main(argv=None):
    """Run main."""
    start_time = datetime.now()
    args = get_args()  # Get args
    logger = load_logger()  # Set logger
    logger.info('PROGRAM STARTED')
    pid = str(os.getpid())
    pidfile = "/tmp/pyHomeVM.pid"
    config = load_config(args.config_file_path)  # load config file
    if os.path.isfile(pidfile):
        logger.info('Program already running')
        html = load_html(config)
        email = load_email(config)
        sendMailLog(CONSTANTS['log_file_path'], email, html)
        sys.exit()
    file(pidfile, 'w').write(pid)
    (ffmpeg, local) = load_core(config)  # load core configs
    remote = load_remote(config)
    html = load_html(config)
    sms = load_sms(config)
    email = load_email(config)
    if(args.log):
        email = load_email(config)
        if(args.report):
            html = load_html(config)
    if(args.remote):
        remote = load_remote(config)
    if(args.sms):
        sms = load_sms(config)
    video_db = shelve.open(CONSTANTS['video_db_path'], writeback=True)
    try:
        if not os.path.exists(CONSTANTS['structure_file_path']):
            raise Exception("Directory structure definition file not found.")
        past_structure = readStructureFromFile(CONSTANTS)
    except Exception:
        logger.info(traceback.format_exc())
        logger.info('{} not found'.format(CONSTANTS['structure_file_path']))
        past_structure = {}  # Start as new
    new_structure = read_structure(local)
    video_ids = get_new_file_ids_from_structure(new_structure, video_db)
    check_and_correct_videos_errors(video_ids, video_db, local, ffmpeg)
    logger.info('Checked for errors and corrupted')
    html_data = updateStructure(
        past_structure,
        read_structure(local),
        local,
        ffmpeg,
        remote,
        video_db)
    sms_sent_file = os.path.join(CONSTANTS['script_root_dir'], 'sms_sent')
    if(mount(remote)):
        logger.info('Mount succesfull')
        syncDirTree(local, remote)
        transferLongVersions(local, remote, video_db)
        if(os.path.isfile(CONSTANTS['todo_file_path'])):
            executeToDoFile(CONSTANTS['todo_file_path'], local, CONSTANTS)
        if(os.path.exists(sms_sent_file)):
            os.remove(sms_sent_file)
            logger.info('sms_sent file has been deleted')
        clean_remote(remote)
        umount(remote)
    else:
        logger.info('Mount unssuccesfull')
        if(not os.path.exists(sms_sent_file) and args.sms):
            sendSmsNotification(sms)
            logger.info('Sms sent')
            with open(sms_sent_file, 'w') as sms_not:
                msg = 'SMS has been sent {}'.format(CONSTANTS['TODAY'])
                sms_not.write(msg)
                logger.info(msg)
    if(args.report and (
            html_data['new'] != '' or
            html_data['modified'] != '' or
            html_data['deleted'] != '' or
            html_data['moved'] != '')):
        html_report = build_html_report(html_data, CONSTANTS, html)
        sendMailReport(html_report, email)
        logger.info('Mail report sent')
    if(args.log):
        sendMailLog(CONSTANTS['log_file_path'], email, html)
        logger.info('log file sent')
    clean_video_db(video_db)
    check_mkv_videos(local, video_db)
    logger.info('DB cleaned')
    video_db.close()
    logger.info('Script ran in {}'.format(datetime.now() - start_time))
    os.unlink(pidfile)
if __name__ == "__main__":
    sys.exit(main())
