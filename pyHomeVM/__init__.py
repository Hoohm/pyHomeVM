__all__ = ["notifications", "settings", "classes", "CONSTANTS", "core"]
from settings.settings import *
from core import *
from CONSTANTS import CONSTANTS
import shelve

video_db = shelve.open(CONSTANTS['video_db_path'], writeback=True)
config = load_config('settings/dev_config.cfg')
(ffmpeg, local) = load_core(config)
html = load_html(config)
remote = load_remote(config)
email = load_email(config)
sms = load_sms(config)