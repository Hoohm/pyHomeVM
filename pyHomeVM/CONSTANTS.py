import os
from datetime import datetime

SCRIPT_ROOT_DIR = os.path.join(os.getcwd(), 'pyHomeVM')
TODO_FILE_PATH = os.path.join(SCRIPT_ROOT_DIR, 'todo.sh')
STRUCTURE_FILE_PATH = os.path.join(SCRIPT_ROOT_DIR, 'structure.json')
CHAPTERS_FILE_NAME = 'chapters.txt'
TODAY = datetime.now().strftime("%Y%m%d")
LOG_FILE_PATH = os.path.join(SCRIPT_ROOT_DIR, 'logs', 'log_{}.txt'.format(TODAY))
HTML_HEADER_PATH = os.path.join(SCRIPT_ROOT_DIR, 'templates', 'custom', 'header.html')
HTML_FOOTER_PATH = os.path.join(SCRIPT_ROOT_DIR, 'templates', 'custom', 'footer.html')
HTML_BODY_PATH = os.path.join(SCRIPT_ROOT_DIR, 'templates', 'body.html')
VIDEO_DB_PATH = os.path.join(SCRIPT_ROOT_DIR, 'video.db')
LOGO_FILE_PATH = os.path.join(SCRIPT_ROOT_DIR, 'templates', 'media', 'logo.png')

CONSTANTS = {
    'script_root_dir': SCRIPT_ROOT_DIR,
    'todo_file_path': TODO_FILE_PATH,
    'structure_file_path': STRUCTURE_FILE_PATH,
    'chapters_file_name': CHAPTERS_FILE_NAME,
    'TODAY': TODAY,
    'log_file_path': LOG_FILE_PATH,
    'html_header_path': HTML_HEADER_PATH,
    'html_footer_path': HTML_FOOTER_PATH,
    'html_body_path': HTML_BODY_PATH,
    'video_db_path': VIDEO_DB_PATH,
    'logo_file_path': LOGO_FILE_PATH}
